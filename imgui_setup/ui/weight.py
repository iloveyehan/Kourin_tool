from imgui_bundle import imgui
def lazy_weight(self):
    from ..imgui_global import GlobalImgui
    GlobalImgui.get().btn_text.new("1/6##asign_weight",tp='给选择的顶点设置权重',ops=self)
    imgui.same_line()
    GlobalImgui.get().btn_text.new("1/3##asign_weight",tp='给选择的顶点设置权重',ops=self)
    imgui.same_line()
    GlobalImgui.get().btn_text.new("2/3##asign_weight",tp='给选择的顶点设置权重',ops=self)
    imgui.same_line()
    GlobalImgui.get().btn_text.new("1/4##asign_weight",tp='给选择的顶点设置权重',ops=self)
    imgui.same_line()
    
    GlobalImgui.get().btn_text.new("1/2##asign_weight",tp='给选择的顶点设置权重',ops=self)
    imgui.same_line()
    
    GlobalImgui.get().btn_text.new("3/4##asign_weight",tp='给选择的顶点设置权重',ops=self)
    imgui.same_line()
    GlobalImgui.get().btn_text.new("1##asign_weight",tp='给选择的顶点设置权重',ops=self)