import time
import bpy
from mathutils import Quaternion, Vector

from ..utils.mesh_data_transfer import MeshData
def comfirm_one_arm(obj):
    n=0     
    for m in obj.modifiers:
        if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
            n=n+1
    if n>1:
        return False
    return True
def get_arm_modi_obj(obj):    
    for m in obj.modifiers:
        if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
            return m
    return False
def pose_to_reset(armature):
    '''传入骨骼物体,应用所在物体的修改器,然后应用为静置姿势,并且重新设置修改器'''
    if armature.type=='ARMATURE':
        # 找到一个 3D 视图 area 和它的 region
        area_3d = next(area for area in bpy.context.window.screen.areas if area.type == 'VIEW_3D')
        region_3d = next(reg for reg in area_3d.regions if reg.type == 'WINDOW')
        
        bpy.ops.object.mode_set(mode='POSE')
        armature_name=armature.name
        rotate=Quaternion((1.0, 0.0, 0.0, 0.0))
        scale=Vector((1.0, 1.0, 1.0))
        location=Vector((0.0, 0.0, 0.0))
        #有变化的顶点组缓存
        # vg_buf=[]
        # for b in bpy.context.object.pose.bones:
        #     if rotate!=b.rotation_quaternion or scale!=b.scale or location!=b.location:
        #         vg_buf.append(b.name)
        vg_set = set()
        for b in bpy.context.object.pose.bones:
            if rotate != b.rotation_quaternion or scale != b.scale or location != b.location:
                # 把自身加入
                vg_set.add(b.name)
                # 递归/栈遍历所有子孙
                stack = [b]
                while stack:
                    pb = stack.pop()
                    # pb.children 是 PoseBone 的子骨骼列表
                    for child in pb.children:
                        if child.name not in vg_set:
                            vg_set.add(child.name)
                            stack.append(child)
        #物体缓存,待处理物体
        objs=[]
        for o in bpy.context.scene.objects:
            for vg in vg_set:
                if vg in o.vertex_groups:
                    objs.append(o)
                    break
        #对每个物体进行处理
        for o in objs:
            override = {
                'window': bpy.context.window,
                'screen': bpy.context.window.screen,
                'area': area_3d,
                'region': region_3d,
                'scene': bpy.context.scene,
                'active_object': o,
                'object': o,
                'selected_objects': [o],
                'selected_editable_objects': [o],
            }
            #mod缓存,后面恢复
            mod_target=None
            mod_temp = o.modifiers[:]
            mod_off = {}
            #判断是否处理这个模型
            do=False
            for modi in mod_temp:
                if modi.type=='ARMATURE' and modi.object==armature and modi.show_viewport:
                    do=True
            if not do:
                continue
            for modi in mod_temp:
                # 记录修改器状态
                # mod_off[modi.name] = o.modifiers[modi.name].show_viewport

                if modi.type=='ARMATURE' and modi.object==armature:
                    if modi.show_viewport:
                        mod_target=modi
                        
                else:
                    # 暂时关闭其他修改器
                    o.modifiers[modi.name].show_viewport = False
            if mod_target is not None:
                mod_temp.remove(mod_target)
            #如果只有basis 给他应用掉
            if o.data.shape_keys:
                if len(o.data.shape_keys.key_blocks)==1:
                    #只有basis
                    sk_array=None
                elif len(o.data.shape_keys.key_blocks)>1:
                    # 生成meshdata
                    apply_single = MeshData(o, deformed=True)
                    # 生成形态键坐标组,形态键值 清单
                    sk_array = apply_single.get_shape_keys_vert_pos()
                    sk_values = apply_single.store_shape_keys_name_value()
            else:
                #没有形态键
                sk_array=None
            
            
            # 删除形态键 应用修改器
            with bpy.context.temp_override(**override):
                bpy.ops.object.modifier_copy(modifier=mod_target.name)
                if o.data.shape_keys:
                    bpy.ops.object.shape_key_remove(all=True)
                if mod_target in o.modifiers[:]:
                    bpy.ops.object.modifier_apply(modifier=mod_target.name)
            if sk_array is not None:
                for sk in sk_array:
                    apply_single.set_position_as_shape_key(shape_key_name=sk, co=sk_array[sk], value=sk_values[sk])

            for modi in mod_temp:
                try:
                    o.modifiers[modi.name].show_viewport = mod_off[modi.name]
                except:
                    print(11)
            
        #应用姿态
        # 删除形态键 应用修改器
        with bpy.context.temp_override(active_object=armature):
            bpy.ops.pose.armature_apply(selected=False)

full_skeleton_dict={
    'Head':['Head','head'],
    'Neck':['Neck','neck'],
    'Shoulder_L':['Shoulder_L','shoulder_l','leftshoulder','left shoulder','Shoulder.L','Shoulder.l','Left shoulder'],
    'Upperarm_L':['Upper_Arm_L','Upper_arm_L','Left arm','Upperarm_L','Upperarm_l','Upperarm.L','Upperarm.l','UpperArm_L','UpperArm_l','UpperArm.L','UpperArm.l','Upper_arm.L','Upper_arm.l'],
    'UpperArm_twist_L':['UpperArm_Twist_L','Upper_arm_Twist.L','UpperArmTwist_L','Upper_arm_Twist_L','UpperArm.Support.L','XC_ArmTwist_L','Upper_arm_support.L','UpperArm_twist_L','Elbow_support.L','Upper_twist.L','Arm_twist.L','Arm_twist.l'],
    'Lowerarm_L':['Lower_Arm_L','Lower_arm_L','Left elbow','Lowerarm_L','Lowerarm_l','Lowerarm.L','Lowerarm.l','LowerArm_L','LowerArm_l','LowerArm.L','LowerArm.l','Lower_arm.L','Lower_arm.l'],
    'LowerArm_twist_L':['LowerArm_Twist_L','Lower_arm_Twist.L','LowerArmTwist_L','Lower_arm_Twist_L','LowerArm.Support.L','XC_WristTwist_L','Lower_arm_support.L','LowerArm_twist_L','Z_LowerArm_twist_L','Wrist_support.L','Lower_twist.L'],
    'Hand_L':['Hand_L','Hand_l','Hand.L','Hand.l','Left Hand','Wrist_L','Left wrist'],
    #大拇指
    'Thumb Proximal_L':['Thumb1Dummy_L','Thumb1_L','Thumb_Proximal_L','Thumb Proximal_L','ThumbProximal.L','Thunb1_L','ThumbProximal_L','Thumb Proximal.L',],
    'Thumb Intermediate_L':['Thumb2Dummy_L','Thumb2_L','Thumb_Intermediate_L','Thumb Intermediate_L','ThumbIntermediate.L','Thunb2_L','ThumbIntermediate_L','Thumb Intermediate.L'],
    'Thumb Distal_L':['Thumb3Dummy_L','Thumb3_L','Thumb_Distal_L','Thumb Distal_L','ThumbDistal.L','Thunb3_L','ThumbDistal_L','Thumb Distal.L',],

    'Index Proximal_L':['Index1_L','Index_Proximal_L','Index Proximal_L','IndexProximal.L','Index1_L','Index Proximal.L','IndexInterProxima.L','IndexProximal_L','IndexProximal_L'],
    'Index Intermediate_L':['Index2_L','Index_Intermediate_L','Index Intermediate_L','IndexIntermediate.L','Index2_L','Index Intermediate.L','IndexIntermediate_L'],
    'Index Distal_L':['Index_Distal_L','Index Distal_L','IndexDistal.L','Index3_L','Index Distal.L','IndexDistal_L'],

    'Middle Proximal_L':['Middle_Proximal_L','Middle Proximal_L','MiddleProximal.L','Middle1_L','MiddleProxima.L','MiddleProximal_L','Middle Proximal.L'],
    'Middle Intermediate_L':['Middle_Intermediate_L','Middle Intermediate_L','MiddleIntermediate.L','Middle2_L','MiddleIntermediate_L','Middle Intermediate.L'],
    'Middle Distal_L':['Middle_Distal_L','Middle Distal_L','MiddleDistal.L','Middle3_L','MiddleDistal_L','Middle Distal.L'],

    'Ring Proximal_L':['Ring_Proximal_L','Ring Proximal_L','RingProximal.L','Ring1_L','RingProxima.L','RingProximal_L','Ring Proximal.L'],
    'Ring Intermediate_L':['Ring_Intermediate_L','Ring Intermediate_L','RingIntermediate.L','Ring2_L','RingIntermediate_L','Ring Intermediate.L'],
    'Ring Distal_L':['Ring_Distal_L','Ring Distal_L','RingDistal.L','Ring3_L','RingDistal_L','Ring Distal.L'],
    
    'Little Proximal_L':['Pinky1_L','Little_Proximal_L','Little Proximal_L','LittleProximal.L','Little1_L','LittleProxima.L','LittleProximal_L','Little Proximal.L'],
    'Little Intermediate_L':['Pinky2_L','Little_Intermediate_L','Little Intermediate_L','LittleIntermediate.L','Little2_L','LittleIntermediate_L','Little Intermediate.L'],
    'Little Distal_L':['Pinky3_L','Little_Distal_L','Little Distal_L','LittleDistal.L','Little3_L','LittleDistal_L','Little Distal.L'],

    'Chest':['Chest','chest'],
    'Spine':['Spine','spine'],
    'Hips':['Hips','hips','hip','Hip','HIP','HIPS'],

    'Butt_L':['Butt_L','Butt_l','Butt.L','Butt.l',],

    'Upperleg_L':['Upper_Leg_L','Upper_leg_L','Left leg','Upperleg_L','UpperLeg.L','Upperleg_l','UpperLeg.l','UpperLeg_L','UpperLeg_l','Upper_leg.L','Upper_leg.l',],
    'knees_L':['knees_L','Z_knees_L','knees_l','Z_knees_l'],
    'Lowerleg_L':['Lower_Leg_L','lower_leg_L','Lower_leg_L','Lower_Leg_L','Lower_Leg_L','lower_leg_l','Lower_leg_l','Lower_Leg_l','Lower_Leg_l','Left knee','Lowerleg_L','LowerLeg.L','Lowerleg_l','LowerLeg.l','LowerLeg_L','LowerLeg_l','Lower_leg.L','Lower_leg.l'],
    'Foot_L':['Left ankle','Toe_Base_L','Foot_L','Foot.L','foot.L','Foot_l','Foot.l','foot.l'],
    'Toe_L':['Left Toe','Toe_L','Toe.L','Toe_l','Toe.l','Toes_L'],

    'Shoulder_R':['Shoulder_R','shoulder_r','rightshoulder','right shoulder','Shoulder.R','Shoulder.r','Right shoulder'],
    'Upperarm_R':['Upper_Arm_R','Upper_arm_R','Right arm','Upperarm_R','Upperarm_r','Upperarm.R','Upperarm.r','UpperArm_R','UpperArm_r','UpperArm.R','UpperArm.r','Upper_arm.R','Upper_arm.r'],
    'UpperArm_twist_R':['UpperArm_Twist_R','Upper_arm_Twist.R','UpperArmTwist_R','Upper_arm_Twist_R','UpperArm.Support.R','XC_ArmTwist_R','Upper_arm_support.R','UpperArm_twist_R','Elbow_support.R','Upper_twist.R','Arm_twist.R','Arm_twist.r'],
    'Lowerarm_R':['Lower_Arm_R','Lower_arm_R','Right elbow','Lowerarm_R','Lowerarm_r','Lowerarm.R','Lowerarm.r','LowerArm_R','LowerArm_r','LowerArm.R','LowerArm.r','Lower_arm.R','Lower_arm.r'],
    'LowerArm_twist_R':['LowerArm_Twist_R','Lower_arm_Twist.R','LowerArmTwist_R','Lower_arm_Twist_R','LowerArm.Support.R','XC_WristTwist_R','Lower_arm_support.R','LowerArm_twist_R','Z_RowerArm_twist_R','Wrist_support.R','Lower_twist.R'],
    'Hand_R':['Hand_R','Hand_r','Hand.R','Hand.r','Right Hand','Wrist_R','Right wrist'],
    #大拇指
    'Thumb Proximal_R':['Thumb1Dummy_R','Thumb1_R','Thumb Proximal_R','ThumbProximal.R','Thunb1_R','ThumbProximal_R','Thumb Proximal.R','Thumb_Proximal_R'],
    'Thumb Intermediate_R':['Thumb2Dummy_R','Thumb2_R','Thumb Intermediate_R','ThumbIntermediate.R','Thunb2_R','ThumbIntermediate_R','Thumb Intermediate.R','Thumb_Intermediate_R'],
    'Thumb Distal_R':['Thumb3Dummy_R','Thumb3_R','Thumb Distal_R','ThumbDistal.R','Thunb3_R','ThumbDistal_R','Thumb Distal.R','Thumb_Distal_R'],

    'Index Proximal_R':['Index Proximal_R','IndexProximal.R','Index1_R','Index Proximal.R','IndexInterProxima.R','IndexProximal_R','IndexProximal_R','Index_Proximal_R'],
    'Index Intermediate_R':['Index Intermediate_R','IndexIntermediate.R','Index2_R','Index Intermediate.R','IndexIntermediate_R','Index_Intermediate_R'],
    'Index Distal_R':['Index Distal_R','IndexDistal.R','Index3_R','Index Distal.R','IndexDistal_R','Index_Distal_R'],

    'Middle Proximal_R':['Middle Proximal_R','MiddleProximal.R','Middle1_R','MiddleProxima.R','MiddleProximal_R','Middle Proximal.R','Middle_Proximal_R'],
    'Middle Intermediate_R':['Middle Intermediate_R','MiddleIntermediate.R','Middle2_R','MiddleIntermediate_R','Middle Intermediate.R','Middle_Intermediate_R'],
    'Middle Distal_R':['Middle Distal_R','MiddleDistal.R','Middle3_R','MiddleDistal_R','Middle Distal.R','Middle_Distal_R'],

    'Ring Proximal_R':['Ring Proximal_R','RingProximal.R','Ring1_R','RingProxima.R','RingProximal_R','Ring Proximal.R','Ring_Proximal_R'],
    'Ring Intermediate_R':['Ring Intermediate_R','RingIntermediate.R','Ring2_R','RingIntermediate_R','Ring Intermediate.R','Ring_Intermediate_R'],
    'Ring Distal_R':['Ring Distal_R','RingDistal.R','Ring3_R','RingDistal_R','Ring Distal.R','Ring_Distal_R'],
    
    'Little Proximal_R':['Pinky1_R','Little Proximal_R','LittleProximal.R','Little1_R','LittleProxima.R','LittleProximal_R','Little Proximal.R','Little_Proximal_R'],
    'Little Intermediate_R':['Pinky2_R','Little Intermediate_R','LittleIntermediate.R','Little2_R','LittleIntermediate_R','Little Intermediate.R','Little_Intermediate_R'],
    'Little Distal_R':['Pinky3_R','Little Distal_R','LittleDistal.R','Little3_R','LittleDistal_R','Little Distal.R','Little_Distal_R'],



    'Butt_R':['Butt_R','Butt_r','Butt.R','Butt.r',],

    'Upperleg_R':['Upper_Leg_R','lower_leg_R','Lower_leg_R','Lower_Leg_R','Lower_Leg_R','lower_leg_r','Lower_leg_r','Lower_Leg_r','Lower_Leg_r','Upperleg_R','UpperLeg.R','Upperleg_r','UpperLeg.r','UpperLeg_R','UpperLeg_r','Upper_leg.R','Upper_leg.r','Right leg'],
    'knees_R':['knees_R','Z_knees_R','knees_r','Z_knees_r'],
    'Lowerleg_R':['Lower_Leg_R','Lowerleg_R','LowerLeg.R','Lowerleg_r','LowerLeg.r','LowerLeg_R','LowerLeg_r','Lower_leg.R','Lower_leg.r','Right knee'],
    'Foot_R':['Foot_R','Toe_Base_R','Foot.R','foot.R','Foot_r','Foot.r','foot.r','Right ankle'],
    'Toe_R':['Toe_R','Toe.R','Toe_r','Toe.r','Right Toe','Toes_R'],
}

def finde_common_bones():
    global full_skeleton_dict
    armature_active=bpy.context.active_object
    armature_other = [obj for obj in bpy.context.selected_objects if obj != armature_active and obj.type == 'ARMATURE'][0]
        
    buf_active={}
    buf_other={}
    buf_match={}
    a=time.time()
    for k in full_skeleton_dict:
        for b in armature_active.data.bones:
            if b.name in full_skeleton_dict[k]:
                if not k in buf_active:
                    buf_match[k]=[b.name]
                    buf_active[k]=[b.name]
                break

    print(time.time()-a)
    for k in full_skeleton_dict:
        for bone in armature_other.data.bones:
            if bone.name in full_skeleton_dict[k]:
                if not k in buf_other:
                    buf_other[k]=[bone.name]
                if k in buf_match:
                    buf_match[k].append(bone.name)
                break

    # buf_list={}
    for k in buf_match:
        if len(buf_match[k])!=2:
            if k in buf_other:
                del buf_other[k]
        else:
            pass
    for k in buf_other:
        try:
            armature_other.data.bones[buf_other[k][0]].name=buf_active[k][0]
        except:
            print(f'有错误:k {k} ')


