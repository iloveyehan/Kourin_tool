import bpy, time
import numpy as np
from bpy.types import Operator
from bpy.props import *
from mathutils import Vector, kdtree


def set_actvg_of_selobjs():
	src_obj = bpy.context.view_layer.objects.active
	finish_obj_l = []
	if not src_obj.mode == "EDIT":
		return finish_obj_l

	actvg_name = src_obj.vertex_groups.active.name
	for tgt_obj in bpy.context.selected_objects:
		bpy.context.view_layer.objects.active = tgt_obj

		if not tgt_obj.vertex_groups:
			continue

		if actvg_name in tgt_obj.vertex_groups:
			tgt_obj.vertex_groups.active = tgt_obj.vertex_groups[actvg_name]

		finish_obj_l.append(tgt_obj)

	bpy.context.view_layer.objects.active = src_obj
	return finish_obj_l
class Kourin_OT_weight_set(Operator):
	bl_idname = "kourin.set_weight"
	bl_label = "Set Weight"
	bl_description = "Set weight values ​​to selected vertices.\nIn edit mode, it works for selected vertices of all multiple objects"
	bl_options = {'REGISTER', 'UNDO'}

	weight : FloatProperty(default=0, name = "Value",min=0,max=1.0)

	items = [
	("Deform Pose Bone", "Deform Pose Bone","Deform Bone Only\nBone must be selected", "BONE_DATA",1),
	("Selected Pose Bone", "Selected Pose Bone","Select Bone\nBone must be selected", "MOD_SIMPLEDEFORM",2),
	("All", "All","All", "RNA_ADD",3),
	("Active", "Active","Active", "RNA",4),
	("None", "None","None", "RADIOBUT_OFF",5),
		]

	normalize : EnumProperty(default="Deform Pose Bone",items=items, name="Normalize")
	normalize_lock_active : BoolProperty(default=True,name="Lock Active")
	items = [
		("REPLACE", "Replace", "", 1),
		("ADD", "Add", "", 2),
		("SUBTRACT", "Subtract", "", 3),
		]
	type : EnumProperty(default="REPLACE",items=items, name="Mix Mode")

	items = [
		("NONE", "None", "", 0),
		("REPLACE", "Replace", "", 1),
		("ADD", "Add", "", 2),
		("SUBTRACT", "Subtract", "", 3),
		]
	type_another_mode : EnumProperty(default="NONE",items=items, name="Mix Mode")

	items = [
		("NONE","None","","RADIOBUT_OFF",0),
		("ACTIVE","Active Vertex Group","","DOT",1),
		("ALL","All Vertex Groups","","SNAP_VERTEX",2),
		]
	set_weight_clean_mode : EnumProperty(default="ACTIVE",items=items, name="Clean",description="Remove Cvertex group assignments which are not required")
	set_weight_clean_limit : FloatProperty(name="Limit",min=0,max=0.99)
	set_weight_clean_keep_single : BoolProperty(name="Keep Single")
	use_symmetry_x : BoolProperty(name="Symmetry X")
	use_symmetry_y : BoolProperty(name="Symmetry Y")
	use_symmetry_z : BoolProperty(name="Symmetry Z")
	symmetry_dist : FloatProperty(name="Symmetry Distance",description="Allowable distance of vertices for symmetry", default=0.001, min=0, step=0.01, precision=4,subtype="DISTANCE")
	set_actvg_of_selobjs : BoolProperty(name="Switch the Active VG of the SelObjs to the Same",description="Set the active vertex group of the selected object the same name as the active vertex group of the active object.\nIt works if you have a vertex group with the same name")
	is_multi_objs : BoolProperty()



	def invoke(self, context,event):
		wpaint = bpy.context.scene.tool_settings.weight_paint
		self.old_time = time.time()



		
		self.type = self.type_another_mode
	
		self.normalize = 'None'

		self.set_weight_clean_mode = None
		self.symmetry_dist = 0.001

		if bpy.app.version >= (2,91,0):
			obj = bpy.context.object
			self.use_symmetry_x = obj.data.use_mirror_x
			self.use_symmetry_y = obj.data.use_mirror_y
			self.use_symmetry_z = obj.data.use_mirror_z
		else:
			wpaint = bpy.context.scene.tool_settings.weight_paint
			self.use_symmetry_x = wpaint.use_symmetry_x
			self.use_symmetry_y = wpaint.use_symmetry_y
			self.use_symmetry_z = wpaint.use_symmetry_z



		return self.execute(context)




	def execute(self, context):
		# props = bpy.context.scene.lazyweight




		self.kd_dic = {}
		self.old_act = bpy.context.view_layer.objects.active
		self.old_mode = self.old_act.mode

		for obj in bpy.context.selected_objects:
			if not obj.type == "MESH":
				continue

			bpy.context.view_layer.objects.active = obj
			obj_dic = {}
			bm_v = obj.data.vertices
			size = len(bm_v)

			kd_local = kdtree.KDTree(size)
			for i, v in enumerate(bm_v):
				kd_local.insert(v.co, i)
			kd_local.balance()

			obj_dic["kd_local"] = kd_local
			self.kd_dic[obj.name] = obj_dic


		bpy.context.view_layer.objects.active = self.old_act




		# 複数選択の場合
		if len(bpy.context.selected_objects) >= 2 and bpy.context.object.mode == "EDIT":
			obj_l = bpy.context.selected_objects
			self.is_multi_objs = True


			# 実行前に、自動でアクティブと同じ頂点グループを他の選択オブジェクトでも選択する
			# if props.auto_set_actvg_of_selobjs:
			if len(bpy.context.selected_objects) >= 2:
				set_actvg_of_selobjs()

		else:
			obj_l = [bpy.context.object]
			self.is_multi_objs = False


		# アクティブ頂点グループ名を取得
		actvg_name = ""
		if len(obj_l) >= 2:
			if self.old_act.type == "MESH":
				if self.old_act.vertex_groups:
					actvg_name = self.old_act.vertex_groups.active.name


		# 選択オブジェクトを回す
		for obj in obj_l:
			if not obj.type == "MESH":
				continue
			bpy.context.view_layer.objects.active = obj

			# オブジェクトモードにする
			if not self.old_mode in {"WEIGHT_PAINT", "OBJECT"}:
				bpy.ops.object.mode_set(mode="OBJECT")

			# なければ頂点グループを追加
			self.add_blank_vg(obj)

			# アクティブ選択を切り替え
			if not obj == self.old_act:
				if self.set_actvg_of_selobjs:
					if len(obj_l) >= 2:
						if obj.vertex_groups:
							if actvg_name in obj.vertex_groups:
								obj.vertex_groups.active = obj.vertex_groups[actvg_name]


			act_vg = obj.vertex_groups.active
			v_all = obj.data.vertices
			v_index_l = [v.index for v in v_all if v.select]
			old_sel_l = v_index_l







			# シンメトリの頂点インデックスをリストに追加
			v_index_l = self.add_symmetry_vindex(obj, v_all,v_index_l)

			# ウェイトを割り当て
			act_vg.add(index=v_index_l,weight=self.weight,type=self.type)


			# 正規化




			# 掃除
	



		bpy.context.view_layer.objects.active = self.old_act


		# モードを戻す
		if not self.old_act.mode == self.old_mode:
			bpy.ops.object.mode_set(mode=self.old_mode)


		# self.PropertyをシーンPropertyに設定
		# self.after_set_properties(self.old_act)


		# time_text = time.time() - self.old_time
		# self.report({'INFO'}, "Process Time [%s]" % str(round(time_text,2)))

		return {'FINISHED'}


	# 空の頂点グループを追加
	def add_blank_vg(self,obj):
		if not obj.vertex_groups:
			bpy.ops.object.vertex_group_add()
			obj.vertex_groups.active_index = 0

		if not obj.vertex_groups.active:
			if bpy.context.active_pose_bone:
				bone_name = bpy.context.active_pose_bone.name
				vg_name = [vg.name for vg in obj.vertex_groups]
				if not bone_name in vg_name:
					obj.vertex_groups.new(name=bone_name)
					obj.vertex_groups.active_index = len(obj.vertex_groups) - 1
			else:
				bpy.ops.object.vertex_group_add()
				obj.vertex_groups.active_index = len(obj.vertex_groups) - 1


	# シンメトリの頂点インデックスをリストに追加
	def add_symmetry_vindex(self, obj, v_all,v_index_l):
		if not (self.use_symmetry_x or self.use_symmetry_y or self.use_symmetry_z):
			return v_index_l

		x_minus = 1
		y_minus = 1
		z_minus = 1

		if self.use_symmetry_x:
			x_minus = -1
		if self.use_symmetry_y:
			y_minus = -1
		if self.use_symmetry_z:
			z_minus = -1

		# kdtree を利用して、リストにミラー頂点のインデックスを追加
		for v in v_all:
			if v.select:
				co, index, dist = self.kd_dic[obj.name]["kd_local"].find(Vector((v.co[0] * x_minus, v.co[1] * y_minus, v.co[2] * z_minus)))
				if dist <= self.symmetry_dist:
					v_index_l += [index]

		return v_index_l




