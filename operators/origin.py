import math
from pathlib import Path

import bpy,bmesh
import mathutils
from bpy.props import StringProperty, FloatProperty, EnumProperty, BoolProperty
from mathutils import Vector, Matrix, Quaternion

from ..utils.vert import dict_vert_verts, check_loops, space_calculate_t, calculate_splines, space_calculate_verts, \
    move_verts, get_connected_selections

from ..common.class_loader.auto_load import ClassAutoloader
origin=ClassAutoloader(Path(__file__))
def reg_origin():
    origin.init()
    origin.register()
def unreg_origin():
    origin.unregister()
from bpy.app.translations import pgettext as _
class Cupcko_Space(bpy.types.Operator):
    bl_idname = "cupcko.looptools_space"
    bl_label = "Space"
    bl_description = "Space the vertices in a regular distribution on the loop"
    bl_options = {'REGISTER', 'UNDO'}

    influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    input: EnumProperty(
        name="Input",
        items=(("all", "Parallel (all)", "Also use non-selected "
                "parallel loops as input"),
              ("selected", "Selection", "Only use selected vertices as input")),
        description="Loops that are spaced",
        default='selected'
        )
    interpolation: EnumProperty(
        name="Interpolation",
        items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
              ("linear", "Linear", "Vertices are projected on existing edges")),
        description="Algorithm used for interpolation",
        default='cubic'
        )
    lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    lock_z: BoolProperty(
        name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.prop(self, "interpolation")
        col.prop(self, "input")
        col.separator()

        col_move = col.column(align=True)
        row = col_move.row(align=True)
        if self.lock_x:
            row.prop(self, "lock_x", text="X", icon='LOCKED')
        else:
            row.prop(self, "lock_x", text="X", icon='UNLOCKED')
        if self.lock_y:
            row.prop(self, "lock_y", text="Y", icon='LOCKED')
        else:
            row.prop(self, "lock_y", text="Y", icon='UNLOCKED')
        if self.lock_z:
            row.prop(self, "lock_z", text="Z", icon='LOCKED')
        else:
            row.prop(self, "lock_z", text="Z", icon='UNLOCKED')
        col_move.prop(self, "influence")

    def invoke(self, context, event):
        # load custom settings
        # settings_load(self)
        return self.execute(context)

    def execute(self, context):
        # initialise
        object = bpy.context.active_object
        bm = bmesh.from_edit_mesh(object.data)

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        # settings_write(self)
        # check cache to see if we can save time
        # cached, single_loops, loops, derived, mapping = cache_read("Space",
        #     object, bm, self.input, False)


        # find loops
        # derived, bm_mod, loops = get_connected_input(object, bm, True, self.input)
        derived=0
        bm_mod = bm

        def edgekey(edge):
            return (tuple(sorted([edge.verts[0].index, edge.verts[1].index])))

        # sorts all edge-keys into a list of loops

        edge_keys = [edgekey(edge) for edge in bm_mod.edges if edge.select and not edge.hide]
        loops = get_connected_selections(edge_keys)
        print('loops444', loops)
        loops = check_loops(loops, bm_mod)
        print('loops555', loops)
        # saving cache for faster execution next time
        # if not cached:
        #     cache_write("Space", object, bm, self.input, False, False, loops,
        #         derived, mapping)

        move = []
        print('loops',loops)
        for loop in loops:
            # calculate splines and new positions
            if loop[1]:  # circular
                loop[0].append(loop[0][0])
            tknots, tpoints = space_calculate_t(bm_mod, loop[0][:])
            splines = calculate_splines(self.interpolation, bm_mod,
                                        tknots, loop[0][:])
            move.append(space_calculate_verts(bm_mod, self.interpolation,
                                              tknots, tpoints, loop[0][:-1], splines))
        # move vertices to new locations
        if self.lock_x or self.lock_y or self.lock_z:
            lock = [self.lock_x, self.lock_y, self.lock_z]
        else:
            lock = False
        mapping=False
        move_verts(object, bm, mapping, move, lock, self.influence)

        # cleaning up
        if derived:
            bm_mod.free()
        bmesh.update_edit_mesh(object.data, loop_triangles=True, destructive=True)

        # cache_delete("Space")

        return{'FINISHED'}



class ARIEDGESMOOTH_OT_SelectEdges(bpy.types.Operator):
    bl_idname = "ari_edge_smooth.select_edges"
    bl_label = "Select Edges"
    bl_description = "根据模式选择边（连续边或环形边）"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        settings = context.scene.ari_edge_smooth_settings
        obj = bpy.context.object

        # Ensure the object is in edit mode and a mesh
        if not obj or obj.type != 'MESH' or bpy.context.object.mode != 'EDIT':
            self.report({'WARNING'}, "必须在编辑模式下选择一个网格对象")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')  # 确保在编辑模式

        # 根据模式选择边
        if settings.mode == 'CONTIGUOUS':
            bpy.ops.mesh.select_linked()  # 选择连续边
        elif settings.mode == 'EDGE_RING':
            bpy.ops.mesh.loop_multi_select(ring=True)  # 选择环形边

        self.report({'INFO'}, f"{settings.mode} edges selected")
        return {'FINISHED'}


class ARIEDGESMOOTH_OT_Reset(bpy.types.Operator):
    bl_idname = "ari_edge_smooth.reset"
    bl_label = "Reset Settings"
    bl_description = "重置边缘平滑设置"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        settings = context.scene.ari_edge_smooth_settings
        settings.edge_strength = 4
        settings.repeat_count = 1
        settings.uniform_smooth = True
        settings.mode = 'CONTIGUOUS'
        self.report({'INFO'}, "Settings Reset")
        return {'FINISHED'}

class Cupcko_Edgesmooth_Ot_Apply(bpy.types.Operator):
    bl_idname = "cupcko_edgesmooth.apply"
    bl_label = "Apply Edge Smooth"
    bl_description = "应用边缘平滑效果"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        settings = bpy.context.scene.ari_edge_smooth_settings
        self.edge_smooth(settings)
        return {'FINISHED'}
    def edge_smooth(self,settings):


        obj=bpy.context.object
        bm = bmesh.from_edit_mesh(obj.data)
        import time
        start = time.time()
        from ..utils.edge_smooth import get_selected_chain
        chain = get_selected_chain(bm)
        print('chain:',len(chain))
        # 遍历每条链 subChain
        for i in range(settings.repeat_count):
            for subChain in chain:
                self.AriEdgeSmooth_gloupGo(settings, subChain)
        bmesh.update_edit_mesh(obj.data)
        # self.AriEdgeSmooth_gloupGo(settings,chain)
        # for i in range(self.settings.repeat_count):
        #     self.AriAlignmentSemicircle(chain)

    def getArrayPiece(self,verList, start, piece, leftTrue):
        pieceList = []
        for ii in range(piece):
            if leftTrue:
                num = start + ii
            else:
                num = start - ii
            print('num:',num)
            print('verList:',len(verList))
            pieceList.append(verList[num])
        return pieceList
    def AriEdgeSmooth_gloupGo(self,settings,verList):
        angle=0
        moveTrue = 1
        circleTrue = 1
        distanceTrue = 0
        angleTrue = 0
        plantTrue = 1
        pieces = settings.edge_strength
        regularTrue = settings.uniform_smooth
        verSize = len(verList)
        loopSize = verSize -pieces
        if loopSize < 0:
            loopSize=0
            pieces = verSize
        piecesList=[]
        ii=0
        jj=0
        leftNum=0
        rightNum=0

        while ii <= loopSize:
            print('loopSize', loopSize,'"ii',ii)
            pieceList=[]

            pieceList = self.getArrayPiece(verList, ii, pieces, 1)
            getAng = self.AriAlignmentSemicircle (pieceList, angle, moveTrue, circleTrue, angleTrue, regularTrue, plantTrue)
            ii+=1
            if (ii > loopSize):
                break
            pieceList = self.getArrayPiece(verList, loopSize + 1 -ii, pieces, 1)
            getAng = self.AriAlignmentSemicircle(pieceList, angle, moveTrue, circleTrue, angleTrue, regularTrue, plantTrue)
            ii+=1


    def AriAlignmentSemicircle(self,verList_num,inputAngle,moveTrue,circleTrue,angleTrue,regularTrue,plantTrue):
        if len(verList_num)<2:
            return
        # 获取每个顶点的位置坐标
        verList_pos = [v.co.copy() for v in verList_num]
        target_first_pos = verList_pos[0] # 获取第一个顶点位置
        target_end_pos = verList_pos[len(verList_pos)-1] # 获取最后一个顶点位置
        target_vector = target_end_pos - target_first_pos # 计算向量
        from ..utils.edge_smooth import vector_max_min_ave,vector_max_min_avg
        centerPos = vector_max_min_ave(verList_pos) # 计算中心点位置
        vectorList=[]
        triangleNormal=[]
        # 算每个顶点相对于中心点的向量
        # 计算每个顶点相对于中心点的向量
        for i in range(len(verList_pos)):
            vec1 = verList_pos[i] - centerPos
            vectorList.append(vec1)

            if i + 1 < len(verList_pos):
                vec2 = verList_pos[i + 1] - centerPos
            else:
                vec2 = verList_pos[0] - centerPos

            normal = vec1.cross(vec2)
            if normal.length != 0:
                normal.normalize()
            triangleNormal.append(normal)

        # 计算中心法向量
        centerNormal = sum(triangleNormal, Vector()) / len(triangleNormal)
        if centerNormal.length != 0:
            centerNormal.normalize()
        else:
            centerNormal = Vector((0, 0, 1))
        # 如果不需要使用输入角度，则计算平均角度
        if not angleTrue:
            angleTotal_rad = 0
            for i in range(1, len(verList_pos) - 1):
                angleTotal_rad += (verList_pos[i] - target_first_pos).angle(verList_pos[i] - target_end_pos)
            angleAbe_rad = angleTotal_rad / (len(verList_pos) - 2)
            angleAbe_deg = math.degrees(angleAbe_rad)
            angleAbe_deg = 360 - (angleAbe_deg * 2)
            inputAngle = angleAbe_deg
        # 计算半径
        radAngle = math.radians((360 - inputAngle) / 2.0)
        firstEndPosDistance = (target_first_pos - target_end_pos).length
        distance = (firstEndPosDistance / 2) / math.sin(radAngle)

        if not moveTrue:return inputAngle

        thre = 0.1
        if -thre < inputAngle < thre:
            # 如果输入角度接近0，则执行等距离移动操作
            for ii in range(len(verList_num)):
                per = float(ii) / (len(verList_num) - 1)
                movePos = target_first_pos.lerp(target_end_pos, per)
                verList_num[ii].co = movePos
            return distance
        basePosList = []
        movePosList = []
        verTotal = len(verList_num)
        rot = inputAngle / (verTotal - 1)  # 计算旋转角度

        # 如果需要规则排列，则计算每个顶点的新位置
        # if regularTrue:
        #     """
        #     重构后的圆弧分布算法:
        #     - 基于 pieceList (该列表的首末点不动)
        #     - 计算除首末点外的平均位置 midAvg
        #     - 与首末点首、末一起决定弧面
        #     - 将所有顶点(尤其中间顶点)等角度插值吸附到弧线上
        #     """
        #
        #     pieceCount = len(verList_num)  # 当前片段的顶点总数
        #     if pieceCount < 2:
        #         # 小于2，无法形成弧
        #         return
        #
        #     # (A) 提取首末点位置, 保证首末点不动
        #     firstPos = verList_num[0].co.copy()
        #     lastPos = verList_num[-1].co.copy()
        #
        #     # 若只有2个点, 直接返回(首末点不需要任何移动)
        #     if pieceCount == 2:
        #         return
        #
        #     # (B) 计算中间点的平均位置 midAvg
        #     middleVerts = verList_num[1:-1]  # 除首末外
        #     if len(middleVerts) > 0:
        #         midSum = sum((v.co for v in middleVerts), mathutils.Vector((0, 0, 0)))
        #         midAvg = midSum * (1.0 / len(middleVerts))
        #     else:
        #         # 如果实际上没有中间点, 也可以直接退出(或设为弦中点)
        #         # 这里设为首末点中点(不一定用得上)
        #         midAvg = (firstPos + lastPos) * 0.5
        #
        #     # (C) 由首末点与 midAvg 确定平面
        #     chord = lastPos - firstPos
        #     L = chord.length
        #     if L < 1e-9:
        #         # 首末点几乎重合, 所有点都放在同一点吧
        #         for v in verList_num:
        #             v.co = firstPos
        #         return
        #
        #     # (D) 弧度(角度)由外部传入: inputAngle (已是整段弧的角度, 单位:度)
        #     radAngle = math.radians(inputAngle)  # 转成弧度
        #
        #     # 若角度非常小, 可以用线性插值
        #     if radAngle < 1e-6:
        #         for i, v in enumerate(verList_num):
        #             t = i / (pieceCount - 1)  # 0~1
        #             v.co = firstPos.lerp(lastPos, t)
        #         return
        #
        #     # (E) 计算半径 R
        #     # R = (L/2) / sin( radAngle/2 )
        #     halfChord = 0.5 * L
        #     sinHalf = math.sin(radAngle * 0.5)
        #     if abs(sinHalf) < 1e-9:
        #         # 角度太小, 退化为线
        #         for i, v in enumerate(verList_num):
        #             t = i / (pieceCount - 1)
        #             v.co = firstPos.lerp(lastPos, t)
        #         return
        #     R = halfChord / sinHalf
        #
        #     # (F) 计算圆心到弦中点的垂直距离 h = sqrt(R^2 - (L/2)^2)
        #     tmp = R * R - halfChord * halfChord
        #     if tmp < 0:
        #         tmp = 0
        #     h = math.sqrt(tmp)
        #
        #     # (G) 构建 planeNormal: 由 chord 与 (midAvg - firstPos) 的叉积
        #     planeNormal = chord.cross(midAvg - firstPos)
        #     if planeNormal.length < 1e-9:
        #         # 如果正好三点共线, 换个做法, 或用一个默认朝上 normal
        #         planeNormal = mathutils.Vector((0, 0, 1))
        #     else:
        #         planeNormal.normalize()
        #
        #     # (H) xAxis = chord.normalize(), yAxis = planeNormal.cross(xAxis)
        #     #     其中 xAxis = 弦方向, yAxis = 与弦、planeNormal 同处平面内
        #     xAxis = chord.normalized()
        #     # 先做一个zTemp = planeNormal.cross(xAxis)
        #     zTemp = planeNormal.cross(xAxis)
        #     zTemp.normalize()  # 万一 planeNormal ~ xAxis, 也要检查
        #     # 再 cross 回去,得到真正与 xAxis 垂直的 yAxis
        #     yAxis = xAxis.cross(zTemp)
        #     yAxis.normalize()
        #
        #     # (I) 弦中点
        #     M = (firstPos + lastPos) * 0.5
        #
        #     # 判断 midAvg 在弦的哪一侧, 以决定“ + yAxis*h 还是 - yAxis*h ”
        #     # 用点积检查:
        #     sideDot = (midAvg - M).dot(yAxis)
        #     if sideDot < 0:
        #         yAxis = -yAxis  # 翻转, 确保圆心在 midAvg 那一面
        #
        #     # 圆心
        #     center = M + yAxis * h
        #
        #     # (J) 在弧上均分. 期望首点对应 alpha=0, 末点对应 alpha=radAngle
        #     # => alpha_i = 0 + ( radAngle * i / (pieceCount-1) ), i=0..pieceCount-1
        #     # => 当 alpha=0, 坐标 = center + xAxis*R
        #     # => 当 alpha=radAngle, 坐标 = center + (xAxis*cos(radAngle) + yAxis*sin(radAngle))*R
        #     # 也可以 -radAngle/2 ~ +radAngle/2, 看习惯. 这里选 0~radAngle, 让 i=0 => 首点, i=pieceCount-1 => 末点.
        #
        #     # 先预生成
        #     newPosList = []
        #     for i in range(pieceCount):
        #         alpha = radAngle * (i / (pieceCount - 1))
        #         cosA = math.cos(alpha)
        #         sinA = math.sin(alpha)
        #         # 局部 X' = R*cosA, Y' = R*sinA
        #         pos = center + xAxis * (R * cosA) + yAxis * (R * sinA)
        #         newPosList.append(pos)
        #
        #     # (K) 修正首末点不移动 => newPosList[0] = firstPos, newPosList[-1] = lastPos
        #     newPosList[0] = firstPos
        #     newPosList[-1] = lastPos
        #
        #     # (L) 赋值回顶点
        #     for i, v in enumerate(verList_num):
        #         v.co = newPosList[i]

        # if regularTrue:
        #     for i in range(verTotal):
        #         rad = math.radians(rot * i + 180 - (inputAngle / 2.0))
        #         x = distance * math.sin(rad)
        #         y = distance * math.cos(rad)
        #         basePosList.append(Vector((x, y, 0)))
        #
        #     baseNormal = Vector((0, 0, 1))
        #     base_vector = Vector((-1, 0, 0))
        #     movePosList = basePosList.copy()
        #
        #     vector_cross = base_vector.cross(target_vector)#计算旋转轴
        #     vector_angle = base_vector.angle(target_vector)# 计算旋转角度
        #     if vector_cross.length != 0:#如果旋转轴为零向量，则设置为默认值
        #         vector_cross.normalize()
        #     else:
        #         vector_cross = Vector((0, 0, 1))
        #
        #     # 旋转中心法向量
        #     rot_q = Quaternion(vector_cross, vector_angle)
        #     rotTargetVec = rot_q @ centerNormal
        #
        #     rotTargetFrontVec = Vector((0, rotTargetVec.y, rotTargetVec.z))
        #     first_cross = baseNormal.cross(rotTargetFrontVec)
        #     first_angle = baseNormal.angle(rotTargetFrontVec)
        #     if first_cross.x < 0:
        #         first_angle = -first_angle
        #
        #     # 旋转每个顶点的位置
        #     rot_matrix = mathutils.Matrix.Rotation(first_angle, 4, 'X')
        #     movePosList = [pos @ rot_matrix for pos in movePosList]
        #
        #     # 反向旋转位置数组
        #     rot_q_inv = Quaternion(vector_cross, -vector_angle)
        #     movePosList = [rot_q_inv @ pos for pos in movePosList]
        #
        #     # 平移每个顶点的位置
        #     translateVal = target_first_pos - movePosList[0]
        #     movePosList = [pos + translateVal for pos in movePosList]

        if 1:
            print('如果不需要规则排列，则执行自定义移动操作')
            # 如果不需要规则排列，则执行自定义移动操作
            currentTool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode).idname
            currentToolTrue = currentTool in {"builtin.move", "builtin.rotate", "builtin.scale"}

            if currentToolTrue:
                centerPos = bpy.context.scene.cursor.location  # 如果当前工具是移动、旋转或缩放工具，则获取操纵器位置作为中心点

            for i in range(len(verList_num)):
                movePosList.append(verList_num[i].co.copy())
                crossNormal = target_vector.cross(centerNormal)
                verticalNormal = target_vector.cross(crossNormal)
                if verticalNormal.length == 0:
                    continue

                if plantTrue:
                    # 计算在法向量平面上的投影点
                    plane_co = target_first_pos
                    plane_no = verticalNormal.normalized()
                    point = movePosList[i]
                    plane_point = point - plane_no.dot(point - plane_co) * plane_no
                    movePosList[i] = plane_point

                if circleTrue:
                    # 更新位置为圆上的点
                    circleCenter = ((distance) * math.cos(math.radians(inputAngle / 2))) * (
                        -crossNormal.normalized()) + ((target_first_pos + target_end_pos) / 2)
                    planePosNormalize = (movePosList[i] - circleCenter).normalized()
                    movePosList[i] = distance * planePosNormalize + circleCenter

            # 移动顶点到新位置
            print('verList_num', len(verList_num))
            for i in range(len(verList_num)):
                print(verList_num[i].co, movePosList[i])
                verList_num[i].co = movePosList[i]
        if regularTrue:
            bpy.ops.cupcko.looptools_space()
        return distance
