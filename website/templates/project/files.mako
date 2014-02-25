<%inherit file="base.mako"/>
<%def name="title()">Files</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div class='help-block'>
    <p>To Upload: Drag files from your desktop and drop into folder below or click an upload button.</p>
</div>

<div id="myGrid" class="filebrowser hgrid"></div>

</%def>

<%def name="stylesheets()">
% for stylesheet in tree_css:
<link rel='stylesheet' href='${stylesheet}' type='text/css' />
% endfor
</%def>

<%def name="javascript_bottom()">
% for script in tree_js:
<script type="text/javascript" src="${script}"></script>
% endfor
<script src="/static/js/dropzone-patch.js"></script>
<script>
(function(global) {
// Don't show dropped content if user drags outside grid
global.ondragover = function(e) { e.preventDefault(); };
global.ondrop = function(e) { e.preventDefault(); };

filebrowser = new Rubeus('#myGrid', {
    data: nodeApiUrl + 'files/grid/'
});

})(window);
</script>
</%def>
