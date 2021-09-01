import numpy as np
from IPython.display import HTML, Javascript, display
from meshcat.commands import Delete, SetAnimation, SetObject, SetProperty, SetTransform
from meshcat.geometry import Geometry
from meshcat.path import Path
from pinocchio.visualize.meshcat_visualizer import MeshcatVisualizer

MESH, CAT = ("""
<div id="meshcat-pane" style="height: 400px; width: 100%; overflow-x: auto; overflow-y: hidden; resize:
both">
</div>
""", """
require.config({
  paths: {
      MeshCat: '//aen.im/meshcat'
  }
});

require(["MeshCat"], function(MeshCat) {
    var viewer = new MeshCat.Viewer(document.getElementById("meshcat-pane"));
    const comm = Jupyter.notebook.kernel.comm_manager.new_comm('meshcat')
    comm.on_msg(function(msg) {
        viewer.handle_command(msg.content.data)
    });
})
""")

URL = "https://aen.im/example-robot-data/robots"


class JupyterVisualizer:
    """
    This is mostly a copy-paste from @RussTedrake's https://github.com/rdeits/meshcat-python/pull/74.

    Changes include:
    - removed iframe
    - split meshcat inclusion into HTML() & Javascript()
    - host meshcat somewhere in HTTPS with "Access-Control-Allow-Origin: *"
    - use requirejs to get it (requirejs is already embedded in jupyter notebooks)
    - initialize communication from the client instead of the server
    - removed parts related to colab
    """
    __slots__ = ["path", "channel"]

    def __init__(self, write_html=True):
        self.path = Path(("meshcat", ))
        self.channel = None
        if write_html:
            display(HTML(MESH), Javascript(CAT))
            get_ipython().kernel.comm_manager.register_target('meshcat', self.set_meshcat_channel)

    def set_meshcat_channel(self, comm_, open_msg):
        self.channel = comm_

    @staticmethod
    def view_into(path, channel):
        vis = JupyterVisualizer(write_html=False)
        vis.path = path
        vis.channel = channel
        return vis

    def __getitem__(self, path):
        return JupyterVisualizer.view_into(self.path.append(path), self.channel)

    def _send(self, command):
        self.channel.send(data=command.lower())

    def set_object(self, geometry, material=None):
        return self._send(SetObject(geometry, material, self.path))

    def set_transform(self, matrix=np.eye(4)):
        return self._send(SetTransform(matrix, self.path))

    def set_property(self, key, value):
        return self._send(SetProperty(key, value, self.path))

    def set_animation(self, animation, play=True, repetitions=1):
        return self._send(SetAnimation(animation, play=play, repetitions=repetitions))

    def delete(self):
        return self._send(Delete(self.path))


class URLMeshGeometry(Geometry):
    """Geometry subclass where the mesh is provided by URL.

    Require the client to know how to fetch it:
    https://github.com/nim65s/meshcat/tree/topic/fetch
    """
    def __init__(self, url):
        super().__init__()
        self.url = url

    def lower(self, object_data):
        return {"type": "_meshfile_geometry", "uuid": self.uuid, "url": self.url, "format": self.url[-3:].lower()}


class PinocchioJupyterVisualizer(MeshcatVisualizer):
    """MeshcatVisualizer subclass that use JupyterVisualizer and initialize it by default

    It also provide meshes from example-robot-data by URL.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initViewer()

    def initViewer(self, viewer=None):
        super().initViewer(viewer or JupyterVisualizer())

    def loadMesh(self, geometry_object):
        if "example-robot-data/robots" in geometry_object.meshPath:
            return URLMeshGeometry(URL + geometry_object.meshPath.split("example-robot-data/robots")[-1])
        return super().loadMesh(geometry_object)
