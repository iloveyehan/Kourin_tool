class GlobalProperty:
    _instance = None

    def __init__(self):
        self.imgui_vrc_instance=[]
        self.debug=True

        #权重传送
        self.that_obj=None
        #镜像顶点组
        self.vg_left=False
        self.vg_right=False
        self.vg_middle=False
        self.vg_mul=False
        self.vg_select=False
        self.last_side=''
        self.vg_mirror_search=False

        self._weight_cache={}
        self._sk_search_map = {}  # key: obj.pointer, value: search text
        #同步集合缓存
        self.item_current_idx=0
        self.sync_col=None
        self.current_obj_vg = None
        self.just_switched_obj_vg = False
        self.current_obj_sk = None
        self.just_switched_obj_sk = False
        self.obj_sync_col={}
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = GlobalProperty()
        return cls._instance
def on_blendfile_loaded():
    global GlobalProperty
    gp = GlobalProperty.get()
    gp._sk_search_map.clear()
    gp.obj_sync_col.clear()