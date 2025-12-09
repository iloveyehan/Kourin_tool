# # This code is based on https://github.com/rin-23/RobustSkinWeightsTransferCode/blob/main/src/utils.py
# # by Rinat Abdrashitov (MIT License)
# # 
# # Changes were made to make the code compatible with Blender's data structures
# # and to improve performance and robustness


# import sys
# sys.path.append(r'G:\\work\\001Blender\\blender_init\\addons\\a_imgui\\robust_laplacian\\robust_laplacian\\build\\Release')
# import robust
from . import robust
            
# This file is part of Robust Weight Transfer for Blender.
#
# Portions of this code are based on:
#   RobustSkinWeightsTransferCode (https://github.com/rin-23/RobustSkinWeightsTransferCode/blob/main/src/utils.py)
#   by Rinat Abdrashitov, used under the MIT License (see below).
#
# Changes were made to make the code compatible with Blender's data structures
# and to improve performance and robustness.
#
# Copyright (C) 2025 sentfromspacevr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Attribution: Developed by sentfromspacevr (https://github.com/sentfromspacevr)
#
# ---- Original MIT License Notice Follows ----
#
# The following portions of this file are based on work by Rinat Abdrashitov and are licensed under the MIT License:
#
# Copyright (c) 2024 Rinat Abdrashitov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import numpy as np


def find_closest_point_on_surface(P, V, F):
    """
    Given a number of points find their closest points on the surface of the V,F mesh

    Args:
        P: #P by 3, where every row is a point coordinate
        V: #V by 3 mesh vertices
        F: #F by 3 mesh triangles indices
    Returns:
        sqrD #P smallest squared distances
        I #P primitive indices corresponding to smallest distances
        C #P by 3 closest points
        B #P by 3 of the barycentric coordinates of the closest point
    """
    
    # sqrD,I,C = igl.point_mesh_squared_distance(P, V, F)
    sqrD,I,C = robust.point_mesh_squared_distance(P, V, F)

    F_closest = F[I,:]
    V1 = V[F_closest[:,0],:]
    V2 = V[F_closest[:,1],:]
    V3 = V[F_closest[:,2],:]

    # B = igl.barycentric_coordinates_tri(C, V1, V2, V3)
    B = robust.barycentric_coordinates_tri(C, V1, V2, V3)

    return sqrD,I,C,B

def interpolate_attribute_from_bary(A,B,I,F):
    """
    Interpolate per-vertex attributes A via barycentric coordinates B of the F[I,:] vertices

    Args:
        A: #V by N per-vertex attributes
        B  #B by 3 array of the barycentric coordinates of some points
        I  #B primitive indices containing the closest point
        F: #F by 3 mesh triangle indices
    Returns:
        A_out #B interpolated attributes
    """
    F_closest = F[I,:]
    a1 = A[F_closest[:,0],:]
    a2 = A[F_closest[:,1],:]
    a3 = A[F_closest[:,2],:]

    b1 = B[:,0]
    b2 = B[:,1]
    b3 = B[:,2]

    b1 = b1.reshape(-1,1)
    b2 = b2.reshape(-1,1)
    b3 = b3.reshape(-1,1)
    
    A_out = a1*b1 + a2*b2 + a3*b3

    return A_out


def normalize_vec(v):
    return v/np.linalg.norm(v)


def find_matches_closest_surface(source_verts, source_triangles, source_normals, target_verts, target_normals, source_weights, dDISTANCE_THRESHOLD_SQRD, dANGLE_THRESHOLD_DEGREES, flip_vertex_normal):
    """
    For each vertex on the target mesh find a match on the source mesh.

    Args:
        V1: #V1 by 3 source mesh vertices
        F1: #F1 by 3 source mesh triangles indices
        N1: #V1 by 3 source mesh normals
        
        V2: #V2 by 3 target mesh vertices
        F2: #F2 by 3 target mesh triangles indices
        N2: #V2 by 3 target mesh normals
        
        W1: #V1 by num_bones source mesh skin weights

        dDISTANCE_THRESHOLD_SQRD: scalar distance threshold
        dANGLE_THRESHOLD_DEGREES: scalar normal threshold

    Returns:
        Matched: #V2 array of bools, where Matched[i] is True if we found a good match for vertex i on the source mesh
        W2: #V2 by num_bones, where W2[i,:] are skinning weights copied directly from source using closest point method
    """
    sqrD,I,C,B = find_closest_point_on_surface(target_verts,source_verts,source_triangles)
    
    # for each closest point on the source, interpolate its per-vertex attributes(skin weights and normals) 
    # using the barycentric coordinates
    W2 = interpolate_attribute_from_bary(source_weights,B,I,source_triangles)
    N1_match_interpolated = interpolate_attribute_from_bary(source_normals,B,I,source_triangles)
    
    norm_N1 = np.linalg.norm(N1_match_interpolated, axis=1, keepdims=True)
    norm_N2 = np.linalg.norm(target_normals, axis=1, keepdims=True)
    normalized_N1 = N1_match_interpolated / norm_N1
    normalized_N2 = target_normals / norm_N2

    dot_product = np.einsum('ij,ij->i', normalized_N1, normalized_N2)
    dot_product = np.clip(dot_product, -1.0, 1.0)  # Ensure the dot product is in the valid range for arccos
    rad_angles = np.arccos(dot_product)
    deg_angles = np.degrees(rad_angles)
    is_distance_threshold = sqrD <= dDISTANCE_THRESHOLD_SQRD
    angle_thresholds = np.full(deg_angles.shape, dANGLE_THRESHOLD_DEGREES)

    is_deg_threshold = deg_angles <= angle_thresholds
    if flip_vertex_normal:
        deg_angles_mirror = 180 - deg_angles
        is_deg_threshold = np.logical_or(is_deg_threshold, deg_angles_mirror <= angle_thresholds)

    Matched = np.logical_and(is_distance_threshold, is_deg_threshold)    
    return Matched, W2


def inpaint(V2, F2, W2, Matched, point_cloud):
    """
    Inpaint weights for all the vertices on the target mesh for which  we didnt 
    find a good match on the source (i.e. Matched[i] == False).

    Args:
        V2: #V2 by 3 target mesh vertices
        F2: #F2 by 3 target mesh triangles indices
        W2: #V2 by num_bones, where W2[i,:] are skinning weights copied directly from source using closest point method
        Matched: #V2 array of bools, where Matched[i] is True if we found a good match for vertex i on the source mesh

    Returns:
        W_inpainted: #V2 by num_bones, final skinning weights where we inpainted weights for all vertices i where Matched[i] == False
    """
    
    # if point_cloud:
    #     L, M = robust_laplacian.point_cloud_laplacian(V2)
    # else:
    #     L, M = robust_laplacian.mesh_laplacian(V2, F2)
    L, M =robust.buildPointCloudLaplacian(V2.astype(np.float64),1e-5,30)
    # L = -L # igl and robust_laplacian have different laplacian conventions
    
    # Minv = sp.sparse.diags(1 / M.diagonal()) # divide by zero?

    # Q2 = -L + L*Minv*L
    # Q2 = Q2.astype(np.float64)
    Q2=robust.compute_Q2(L, M)
    # Aeq = sp.sparse.csc_matrix((0, 0), dtype=np.float64)
    Aeq = robust.make_empty_sparse(0,0)
    Beq = np.array([], dtype=np.float64)
    B = np.zeros(shape = (L.shape[0], W2.shape[1]), dtype=np.float64)

    b = np.array(range(0, int(V2.shape[0])), dtype=np.int64)
    b = b[Matched]
    bc = W2[Matched,:].astype(np.float64)
    result, W_inpainted = robust.min_quad_with_fixed(Q2, B, b, bc, Aeq, Beq, True)
    W_inpainted = W_inpainted.astype(np.float32)
    # when W2 shape = (num_verts, 1), it gets flattened to (num_verts, )
    # reshape it back to initial shape, limit_mask expects 2d array
    if result:
        W_inpainted = W_inpainted.reshape(W2.shape)
    return result, W_inpainted # TODO: Add results

