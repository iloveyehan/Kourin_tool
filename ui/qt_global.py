class GlobalProperty:
    _instance = None

    def __init__(self):
        self.imgui_vrc_instance=[]
        self.debug=True


        #镜像顶点组
        self.vg_left=False
        self.vg_right=False
        self.vg_middle=False
        self.vg_mul=False
        self.vg_select=False
        self.last_side=''
        self.vg_mirror_search=False
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