# -*- coding: utf-8 -*-

import re
import copy
import logging
import pyelasticsearch

from requests.exceptions import ConnectionError

from framework import sentry

from website import settings
from website.filters import gravatar
from website.search import exceptions
from website.models import User, Node

logger = logging.getLogger(__name__)


# These are the doc_types that exist in the search database
TYPES = ['project', 'component', 'user', 'registration']

try:
    elastic = pyelasticsearch.ElasticSearch(
        settings.ELASTIC_URI,
        timeout=settings.ELASTIC_TIMEOUT
    )
    logging.getLogger('pyelasticsearch').setLevel(logging.WARN)
    logging.getLogger('requests').setLevel(logging.WARN)
    elastic.health()
except pyelasticsearch.exceptions.ConnectionError as e:
    sentry.log_exception()
    sentry.log_message("The SEARCH_ENGINE setting is set to 'elastic', but there "
                        "was a problem starting the elasticsearch interface. Is "
                        "elasticsearch running?")
    elastic = None


def requires_search(func):
    def wrapped(*args, **kwargs):
        if elastic is not None:
            try:
                return func(*args, **kwargs)
            except pyelasticsearch.exceptions.ElasticHttpError as e:
                raise exceptions.SearchException(e.error)
            except ConnectionError:
                raise exceptions.SearchException('Can not connect to ElasticSearch' )

        sentry.log_message('Elastic search action failed. Is elasticsearch running?')
    return wrapped


@requires_search
def search(raw_query, start=0, size=10, index='website'):
    orig_query = raw_query
    query, filtered_query = _build_query(raw_query, start, size)

    # Get document counts by type
    counts = {}
    count_query = copy.deepcopy(query)
    del count_query['from']
    del count_query['size']
    for type in TYPES:
        try:
            count_query['query']['function_score']['query']['filtered']['filter']['type']['value'] = type
        except KeyError:
            pass

        counts[type + 's'] = elastic.count(count_query, index=index, doc_type=type)['count']

    # Figure out which count we should display as a total
    for type in TYPES:
        if type + ':' in orig_query:
            counts['total'] = counts[type + 's']
    if not counts.get('total'):
        counts['total'] = sum([x for x in counts.values()])

    # Run the real query and get the results
    raw_results = elastic.search(query, index=index)
    results = [hit['_source'] for hit in raw_results['hits']['hits']]
    formatted_results, tags = create_result(results, counts)

    return formatted_results, tags, counts


def _build_query(raw_query, start, size):

    # Default to searching all types with a big 'or' query
    type_filter = {}
    type_filter['or'] = [{
        'type': {
            'value': type
        }
    } for type in TYPES]

    # But make sure to filter by type if requested
    for type in TYPES:
        if type + ':' in raw_query:
            type_filter = {
                'type': {
                    'value': type
                }
            }

    # Cleanup string before using it to query
    for type in TYPES:
        raw_query = raw_query.replace(type + ':', '')

    raw_query = raw_query.replace('(', '').replace(')', '').replace('\\', '').replace('"', '')

    raw_query = raw_query.replace(',', ' ').replace('-', ' ').replace('_', ' ')

    # If the search contains wildcards, make them mean something
    if '*' in raw_query:
        inner_query = {
            'query_string': {
                'default_field': '_all',
                'query': raw_query + '*',
                'analyze_wildcard': True,
            }
        }
    else:
        inner_query = {
            'multi_match': {
                'query': raw_query,
                'type': 'phrase_prefix',
                'fields': '_all',
            }
        }

    # If the search has a tag filter, add that to the query
    if 'tags:' in raw_query:
        tags = raw_query.replace('AND', ' ').split('tags:')
        tag_filter = {
            'query': {
                'match': {
                    'tags': {
                        'query': '',
                        'operator': 'or'
                    }
                }
            }
        }
        for i in range(1, len(tags)):
            for tag in tags[i].split():
                tag_filter['query']['match']['tags']['query'] += ' ' + tag

        # If the query is empty, turn it back to a wildcard search
        if not tags[0].strip():
            inner_query = {
                'query_string': {
                    'default_field': '_all',
                    'query': '*',
                    'analyze_wildcard': True,
                }
            }
        elif inner_query.get('query_string'):
            inner_query['query_string']['query'] = tags[0]
        elif inner_query.get('multi_match'):
            inner_query['multi_match']['query'] = tags[0]

        inner_query = {
            'filtered': {
                'filter': tag_filter,
                'query': inner_query
            }
        }

    # This is the complete query
    query = {
        'query': {
            'function_score': {
                'query': {
                    'filtered': {
                        'filter': type_filter,
                        'query': inner_query
                    }
                },
                'functions': [{
                    'field_value_factor': {
                        'field': 'boost'
                    }
                }],
                'score_mode': 'multiply'
            }
        },
        'from': start,
        'size': 10,
    }

    return query, raw_query


@requires_search
def update_node(node, index='website'):
    from website.addons.wiki.model import NodeWikiPage

    component_categories = ['', 'hypothesis', 'methods and measures', 'procedure', 'instrumentation', 'data', 'analysis', 'communication', 'other']
    category = 'component' if node.category in component_categories else node.category

    if category == 'project':
        elastic_document_id = node._id
        parent_id = None
        category = 'registration' if node.is_registration else category
    elif category == 'report':
        elastic_document_id = node._id
        parent_id = node.parent_id
    else:
        try:
            elastic_document_id = node._id
            parent_id = node.parent_id
            category = 'registration' if node.is_registration else category
        except IndexError:
            # Skip orphaned components
            return

    if node.is_deleted or not node.is_public:
        delete_doc(elastic_document_id, node)
    else:
        elastic_document = {
            'id': elastic_document_id,
            'contributors': [
                x.fullname for x in node.visible_contributors
                if x is not None
                and (x.is_active() or category == 'report')
            ],
            'contributors_url': [
                x.profile_url for x in node.visible_contributors
                if x is not None
                and x.is_active()
            ],
            'description': node.description,
            'title': node.title,
            'category': node.category,
            'public': node.is_public,
            'tags': [tag._id for tag in node.tags if tag],
            'url': node.url,
            'registeredproject': node.is_registration,
            'wikis': {},
            'parent_id': parent_id,
            'iso_timestamp': node.date_created,
            'boost': int(not node.is_registration) + 1,  # This is for making registered projects less relevant
        }
        for wiki in [
            NodeWikiPage.load(x)
            for x in node.wiki_pages_current.values()
        ]:
            elastic_document['wikis'][wiki.page_name] = wiki.raw_text(node)

        try:
            elastic.update(index, category, id=elastic_document_id, doc=elastic_document, upsert=elastic_document, refresh=True)
        except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
            elastic.index(index, category, elastic_document, id=elastic_document_id, overwrite_existing=True, refresh=True)


@requires_search
def update_user(user):
    if not user.is_active() or user.is_system_user:
        try:
            elastic.delete('website', 'user', user._id, refresh=True)
            return
        except pyelasticsearch.exceptions.ElasticHttpNotFoundError as e:
            return

    user_doc = {
        'id': user._id,
        'user': user.fullname,
        'boost': 2,  # TODO(fabianvf): Probably should make this a constant or something
    }

    try:
        elastic.update('website', 'user', doc=user_doc, id=user._id, upsert=user_doc, refresh=True)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        elastic.index("website", "user", user_doc, id=user._id, overwrite_existing=True, refresh=True)


@requires_search
def delete_all():
    indices = [
        'website',
        'metadata',
        'application',
        'application_created'
    ]

    for index in indices:
        try:
            elastic.delete_index(index)
        except pyelasticsearch.exceptions.ElasticHttpNotFoundError as e:
            logger.warn(e)
            logger.warn('The index "{}" was not deleted from elasticsearch'.format(index))


@requires_search
def delete_doc(elastic_document_id, node):
    category = 'registration' if node.is_registration else node.project_or_component
    try:
        elastic.delete('website', category, elastic_document_id, refresh=True)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        logger.warn("Document with id {} not found in database".format(elastic_document_id))


def _load_parent(parent):
    parent_info = {}
    if parent is not None and parent.is_public:
        parent_info['title'] = parent.title
        parent_info['url'] = parent.url
        parent_info['is_registration'] = parent.is_registration
        parent_info['id'] = parent._id
    else:
        parent_info['title'] = '-- private project --'
        parent_info['url'] = ''
        parent_info['is_registration'] = None
        parent_info['id'] = None
    return parent_info


def create_result(results, counts):
    ''' Takes a dict of counts by type, and a list of dicts of the following structure:
    {
        'category': {NODE CATEGORY},
        'description': {NODE DESCRIPTION},
        'contributors': [{LIST OF CONTRIBUTORS}],
        'title': {TITLE TEXT},
        'url': {URL FOR NODE},
        'tags': {LIST OF TAGS},
        'contributors_url': [{LIST OF LINKS TO CONTRIBUTOR PAGES}],
        'id': {NODE ID},
        'parent_id': {PARENT NODE ID},
        'parent_title': {TITLE TEXT OF PARENT NODE},
        'wikis': {LIST OF WIKIS AND THEIR TEXT},
        'public': {TRUE OR FALSE},
        'registeredproject': {TRUE OR FALSE}
    }

    Returns list of dicts of the following structure:
    {
        'contributors': [{LIST OF CONTRIBUTORS}],
        'wiki_link': '{LINK TO WIKIS}',
        'title': '{TITLE TEXT}',
        'url': '{URL FOR NODE}',
        'is_component': {TRUE OR FALSE},
        'parent_title': {TITLE TEXT OF PARENT NODE},
        'parent_url': {URL FOR PARENT NODE},
        'tags': [{LIST OF TAGS}],
        'contributors_url': [{LIST OF LINKS TO CONTRIBUTOR PAGES}],
        'is_registration': {TRUE OR FALSE},
        'highlight': [{No longer used, need to phase out}],
        'description': {PROJECT DESCRIPTION},
    }
    '''
    formatted_results = []
    word_cloud = {}
    visited_nodes = {}  # For making sure projects are only returned once
    index = 0  # For keeping track of what index a project is stored
    for result in results:
        # User results are handled specially
        if 'user' in result:
            formatted_results.append({
                'id': result['id'],
                'user': result['user'],
                'user_url': '/profile/' + result['id'],
            })
            index += 1
        else:
            # Build up word cloud
            for tag in result['tags']:
                word_cloud[tag] = 1 if word_cloud.get(tag) is None \
                    else word_cloud[tag] + 1

            # Ensures that information from private projects is never returned
            parent = Node.load(result['parent_id'])
            parent_info = _load_parent(parent)  # This is to keep track of information, without using the node (for security)

            if visited_nodes.get(result['id']):
                # If node already visited, it should not be returned as a result
                continue
            else:
                visited_nodes[result['id']] = index

            # Format dictionary for output
            result['url']
            formatted_results.append(_format_result(result, parent, parent_info))
            index += 1

    return formatted_results, word_cloud


def _format_result(result, parent, parent_info):
    formatted_result = {
        'contributors': result['contributors'],
        'wiki_link': result['url'] + 'wiki/',
        'title': result['title'],
        'url': result['url'],
        'is_component': False if parent is None else True,
        'parent_title': parent_info['title'] if parent is not None else None,
        'parent_url': parent_info['url'] if parent is not None else None,
        'tags': result['tags'],
        'contributors_url': result['contributors_url'],
        'is_registration': (result['registeredproject'] if parent is None
                                                        else parent_info['is_registration']),
        'highlight': [],
        'description': result['description'] if parent is None else None,
    }

    return formatted_result


@requires_search
def search_contributor(query, exclude=None, current_user=None):
    """Search for contributors to add to a project using elastic search. Request must
    include JSON data with a "query" field.

    :param: Search query, current_user
    :return: List of dictionaries, each containing the ID, full name,
        most recent employment and education, gravatar URL of an OSF user

    """
    query.replace(" ", "_")
    query = re.sub(r'[\-\+]', '', query)
    query = re.split(r'\s+', query)

    if len(query) > 1:
        and_filter = {'and': []}
        for item in query:
            and_filter['and'].append({
                'prefix': {
                    'user': item.lower()
                }
            })
    else:
        and_filter = {
            'prefix': {
                'user': query[0].lower()
            }
        }

    query = {
        'query': {
            'filtered': {
                'filter': and_filter
            }
        }
    }

    results = elastic.search(query, index='website')
    docs = [hit['_source'] for hit in results['hits']['hits']]

    if exclude:
        docs = (x for x in docs if x.get('id') not in exclude)

    users = []
    for doc in docs:
        # TODO: use utils.serialize_user
        user = User.load(doc['id'])

        if current_user:
            n_projects_in_common = current_user.n_projects_in_common(user)
        else:
            n_projects_in_common = 0

        if user is None:
            logger.error('Could not load user {0}'.format(doc['id']))
            continue
        if user.is_active():  # exclude merged, unregistered, etc.
            current_employment = None
            education = None

            if user.jobs:
                current_employment = user.jobs[0]['institution']

            if user.schools:
                education = user.schools[0]['institution']

            users.append({
                'fullname': doc['user'],
                'id': doc['id'],
                'employment': current_employment,
                'education': education,
                'n_projects_in_common': n_projects_in_common,
                'gravatar_url': gravatar(
                    user,
                    use_ssl=True,
                    size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR,
                ),
                'profile_url': user.profile_url,
                'registered': user.is_registered,
                'active': user.is_active()

            })

    return {'users': users}


# ## Metadata stuff ## #

@requires_search
def update_metadata(metadata):
    index = "metadata"
    app_id = metadata.namespace
    data = metadata.to_json()
    elastic.update(index=index, doc_type=app_id, upsert=data, doc=data, id=metadata._id)


@requires_search
def search_metadata(query, _type, start, size):
    if isinstance(query, dict):
        return search_metadata_dict(query, _type)

    query = {
        'query': _metadata_inner_query(query),
        'from': start,
        'size': size,
    }

    return elastic.search(query, index='metadata', doc_type=_type)

def search_metadata_dict(query, _type):
    return elastic.search(query, index='metadata', doc_type=_type)

def _metadata_inner_query(query):
    if query == '*':
        return {
            'query_string': {
                'default_field': '_all',
                'query': '*',
                'analyze_wildcard': True,
            }
        }
    query = query.split(';')
    filters = []
    for item in query:
        item = item.split(':')

        if len(item) == 1:
            item = ['_all', item[0]]
        if len(item[1].split(',')) > 1:
            filters.append({
                'terms': {
                    item[0]: item[1].split(',')
                }
            })
        else:
            filters.append({
                "query": {
                    'match': {
                        item[0]: {
                            'query': item[1],
                            'operator': 'and',
                            'type': 'phrase',
                        }
                    }
                }
            })

    inner_query = {
        'filtered': {
            'filter': {
                'and': filters,
            },
        },
    }
    return inner_query


@requires_search
def get_mapping(index, _type):
    try:
        mapping = elastic.get_mapping(index, _type)[index]['mappings'][_type]['properties']
    except KeyError:
        return None  # For now
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        return None  # No mapping

    return _strings_to_types(mapping)


def _strings_to_types(mapping):
    type_map = {
        u'boolean': bool,
        u'object': dict,
        u'long': int,
        u'int': int,
        u'float': float,
        u'double': float,
        u'null': type(None),
        u'string': str,
    }

    for key, val in mapping.items():
        if val.get('type') and isinstance(val['type'], basestring):
            mapping[key] = type_map.get(val['type'])
        else:
            mapping[key] = _strings_to_types(val)

    return mapping
@requires_search
def get_recent_documents(raw_query='', start=0, size=10):

    query = _recent_document_query(raw_query, start, size)
    raw_results = elastic.search(query, index='website', doc_type='project')
    results = [hit['_source'] for hit in raw_results['hits']['hits']]
    count = raw_results['hits']['total']

    return {'results': results, 'count': count}


def _recent_document_query(raw_query, start=0, size=10):
    inner_query = {}
    if not raw_query or ':' not in raw_query:
        inner_query = {'match_all': {}} if not raw_query else {'match': {'_all': raw_query}}
    else:
        items = raw_query.split(';')
        filters = []
        for item in items:
            item = item.split(':')
            if len(item) == 1:
                item = ['_all', item[0]]

            filters.append({
                "query": {
                    'match': {
                        item[0]: {
                            'query': item[1],
                            'operator': 'and',
                            'type': 'phrase',
                        }
                    }
                }
            })

        inner_query = {
            'filtered': {
                'filter': {
                    'and': filters
                },
            },
        }

    return {
        'sort': [{
            'iso_timestamp': {
                'order': 'desc'
            }
        }],
        'query': inner_query,
        'from': start,
        'size': size
    }
