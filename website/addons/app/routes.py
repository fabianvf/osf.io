# -*- coding: utf-8 -*-
"""Routes for the app addon.
"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

# Routes that use the web renderer
web_routes = {
    'rules': [
        Rule(
            [
                '/project/<pid>/app/',
                '/project/<pid>/node/<nid>/app/',
            ],
            'get',
            views.web.application_page,
            OsfWebRenderer('../addons/app/templates/app_page.mako'),
        ),


    #     ##### Download file #####
    #     Rule(
    #         [
    #             '/project/<pid>/app/files/<path:path>/download/',
    #             '/project/<pid>/node/<nid>/app/files/<path:path>/download/',
    #         ],
    #         'get',
    #         views.crud.app_download,
    #         notemplate,
    #     ),
    ],
}

# JSON endpoints
api_routes = {
    'rules': [

        ##### Node settings #####

        Rule(
            ['/project/<pid>/app/config/',
            '/project/<pid>/node/<nid>/app/config/'],
            'get',
            views.config.app_config_get,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/app/config/',
            '/project/<pid>/node/<nid>/app/config/'],
            'put',
            views.config.app_config_put,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/app/config/',
            '/project/<pid>/node/<nid>/app/config/'],
            'delete',
            views.config.app_deauthorize,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/app/config/import-auth/',
            '/project/<pid>/node/<nid>/app/config/import-auth/'],
            'put',
            views.config.app_import_user_auth,
            json_renderer
        ),
    ],

    ## Your routes here

    'prefix': '/api/v1'
}


custom_routing_routes = {
    'rules': [
        Rule(
            ['/project/<pid>/app/',
             '/project/<pid>/node/<nid>/app/'],
            'get',
            views.crud.query_app,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/q/',
             '/project/<pid>/node/<nid>/app/q/'],
            'get',
            views.crud.list_custom_routes,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/q/',
             '/project/<pid>/node/<nid>/app/q/'],
            'post',
            views.crud.create_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/q/<path:route>/',
             '/project/<pid>/node/<nid>/app/q/<path:route>/'],
            'get',
            views.crud.resolve_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/q/<path:route>/',
             '/project/<pid>/node/<nid>/app/q/<path:route>/'],
            'put',
            views.crud.update_route,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/q/<path:route>/',
             '/project/<pid>/node/<nid>/app/q/<path:route>/'],
            'delete',
            views.crud.delete_route,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}

metadata_routes = {
    'rules': [
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            'get',
            views.crud.get_metadata,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            ['put', 'post'],
            views.crud.add_metadata,
            json_renderer
        ),
        Rule(
            ['/project/<pid>/app/<guid>/',
             '/project/<pid>/node/<nid>/app/<guid>/'],
            'delete',
            views.crud.delete_metadata,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
