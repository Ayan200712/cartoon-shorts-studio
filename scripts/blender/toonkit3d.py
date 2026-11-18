"""Blender toon kit: toon materials with outlines, textured planes/boxes, round-head rigged characters,
camera helpers. Imported by shot scripts running inside Blender (blender -b -P shot.py)."""
import bpy, bmesh, math, os
from mathutils import Vector, Euler

TEX = os.environ.get("TOON_TEX", os.path.join(os.getcwd(), "tex"))
FPS = 30


# ------------------------------------------------------------------ scene
def reset(frames, res=(1080, 1920)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng; break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, frames
    try:
        sc.eevee.taa_render_samples = 24
    except Exception:
        pass
    for attr, val in (("use_gtao", True), ("use_shadows", True)):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    w = bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.8, 0.8, 0.85, 1); bg.inputs[1].default_value = 0.9
    return sc


def world(color, strength=0.9):
    bg = bpy.context.scene.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*color, 1); bg.inputs[1].default_value = strength


def srgb(c):
    """0-255 sRGB -> linear tuple."""
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(f(v) for v in c[:3])


# ------------------------------------------------------------------ materials
_mats = {}


def toon(color, name=None, soft=0.35, rim=0.0, tex=None, emission=0.0):
    """Soft 3D toon: diffuse lit by scene lights + a little emission so shadows never go black."""
    key = name or f"toon_{color}_{tex}_{soft}_{emission}"
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    dif = N.new("ShaderNodeBsdfDiffuse"); dif.inputs[1].default_value = 0.0
    em = N.new("ShaderNodeEmission"); em.inputs[1].default_value = soft * 0.55 + emission
    add = N.new("ShaderNodeAddShader")
    if tex:
        img = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
        it = N.new("ShaderNodeTexImage"); it.image = img
        Lk.new(it.outputs[0], dif.inputs[0]); Lk.new(it.outputs[0], em.inputs[0])
    else:
        col = (*srgb(color), 1)
        dif.inputs[0].default_value = col; em.inputs[0].default_value = col
    Lk.new(dif.outputs[0], add.inputs[0]); Lk.new(em.outputs[0], add.inputs[1])
    Lk.new(add.outputs[0], out.inputs[0])
    _mats[key] = m
    return m


def flat(tex=None, color=(255, 255, 255), name=None, alpha=False, strength=1.0):
    """Unlit (emission) image/colour; alpha-blended when alpha=True (decals)."""
    key = name or f"flat_{tex}_{color}_{alpha}_{strength}"
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); em.inputs[1].default_value = strength
    if tex:
        it = N.new("ShaderNodeTexImage"); it.image = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
        Lk.new(it.outputs[0], em.inputs[0])
    else:
        em.inputs[0].default_value = (*srgb(color), 1)
    if alpha and tex:
        tr = N.new("ShaderNodeBsdfTransparent"); mix = N.new("ShaderNodeMixShader")
        Lk.new(it.outputs[1], mix.inputs[0]); Lk.new(tr.outputs[0], mix.inputs[1]); Lk.new(em.outputs[0], mix.inputs[2])
        Lk.new(mix.outputs[0], out.inputs[0])
        for attr, val in (("blend_method", "HASHED"), ("surface_render_method", "DITHERED")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    else:
        Lk.new(em.outputs[0], out.inputs[0])
    _mats[key] = m
    return m


def ink():
    if "INK" in _mats:
        return _mats["INK"]
    m = bpy.data.materials.new("INK"); m.use_nodes = True
    N = m.node_tree.nodes
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission")
    em.inputs[0].default_value = (0.012, 0.010, 0.014, 1)
    m.node_tree.links.new(em.outputs[0], out.inputs[0])
    m.use_backface_culling = True
    _mats["INK"] = m
    return m


def outline(obj, thickness=0.02):
    """Inverted-hull ink outline."""
    obj.data.materials.append(ink())
    mod = obj.modifiers.new("ink", "SOLIDIFY")
    mod.thickness = -thickness; mod.use_flip_normals = True; mod.offset = 1.0
    mod.material_offset = len(obj.data.materials) - 1
    return obj


def assign(obj, mat):
    obj.data.materials.clear(); obj.data.materials.append(mat)
    return obj


# ------------------------------------------------------------------ primitives
def _link(o):
    bpy.context.collection.objects.link(o) if o.name not in bpy.context.collection.objects else None
    return o


def box(name, size, loc, mat, rot=(0, 0, 0), ol=0.0, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new("bev", "BEVEL"); b.width = bevel; b.segments = 3
    assign(o, mat)
    if ol:
        outline(o, ol)
    return o


def plane(name, w, h, loc, rot, mat, ol=0.0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = (w, h, 1)
    bpy.ops.object.transform_apply(scale=True)
    assign(o, mat)
    if ol:
        sol = o.modifiers.new("thick", "SOLIDIFY"); sol.thickness = 0.01
        outline(o, ol)
    return o


def wall_plane(name, w, h, loc, facing, mat, tile=1.0):
    """Vertical plane facing +Y/-Y/+X/-X, UVs tiled."""
    rot = {"+y": (math.pi / 2, 0, math.pi), "-y": (math.pi / 2, 0, 0), "+x": (math.pi / 2, 0, -math.pi / 2),
           "-x": (math.pi / 2, 0, math.pi / 2), "up": (0, 0, 0), "down": (math.pi, 0, 0)}[facing]
    o = plane(name, w, h, loc, rot, mat)
    if tile != 1.0:
        for l in o.data.uv_layers.active.data:
            l.uv = (l.uv[0] * w / tile, l.uv[1] * h / tile)
    return o


def sphere(name, r, loc, mat, scale=(1, 1, 1), ol=0.0, segs=48):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=segs, ring_count=segs // 2)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.shade_smooth()
    assign(o, mat)
    if ol:
        outline(o, ol)
    return o


def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), ol=0.0, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.active_object; o.name = name
    bpy.ops.object.shade_smooth()
    assign(o, mat)
    if ol:
        outline(o, ol)
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    return o


def parent(child, par, keep=True):
    mw = child.matrix_world.copy()
    child.parent = par
    if keep:
        child.matrix_world = mw


def lamp_light(kind, loc, energy, color=(1, 0.95, 0.85), size=1.0, rot=(0, 0, 0)):
    ld = bpy.data.lights.new(kind + "L", kind)
    ld.energy = energy; ld.color = color
    if kind == "AREA":
        ld.size = size
    if kind == "SUN":
        ld.angle = math.radians(3)
    if kind == "POINT":
        ld.shadow_soft_size = 0.03
    o = bpy.data.objects.new(kind, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    return o


# ------------------------------------------------------------------ characters
STYLE = {
    "kyle": dict(body=(214, 40, 36), hair=(128, 74, 36), tuft=True, tag="tag_kyle.png", badge=True),
    "kyle_suit": dict(body=(150, 92, 44), hair=(128, 74, 36), tuft=True, tie=(240, 190, 60)),
    "trainee": dict(body=(214, 40, 36), hair=(60, 40, 30), tuft=False, tag="tag_trainee.png", badge=True),
    "customer": dict(body=(232, 178, 40), hat="bucket"),
    "agent": dict(body=(40, 54, 92), hat="bucket", tie=(200, 40, 40), badgegold=True),
    "cop": dict(body=(36, 50, 92), hat="cop", badgegold=True),
    "lady": dict(body=(40, 168, 160), curls=(214, 110, 40), chain=True),
    "friend1": dict(body=(120, 70, 160), hair=(40, 30, 30)),
    "friend2": dict(body=(240, 150, 170), hair=(240, 190, 60)),
}


class Char:
    """Round-head stick character. Units: head radius R. Root at feet, facing -Y (towards a camera at -Y)."""

    def __init__(self, name, kind, loc, R=0.3, rot_z=0.0, faces=("neutral",), back=False, legs=True):
        st = STYLE[kind]
        self.R, self.name = R, name
        self.root = empty(name, loc); self.root.rotation_euler = (0, 0, rot_z)
        R = R
        body_h = 1.7 * R
        hip_z = 1.25 * R if legs else 0.0
        self.body_z = hip_z + body_h * 0.5
        neck_z = hip_z + body_h
        head_z = neck_z + 0.82 * R
        self.head_z = head_z
        OLW = R * 0.045
        # legs: hip -> thigh -> knee -> shin (so they can walk and sit)
        self.leg = {}
        if legs:
            for side, sx in (("L", 1), ("R", -1)):
                hp = empty(f"{name}_hip{side}", (sx * R * 0.22, 0, hip_z + 0.05 * R), self.root)
                th = cyl(f"{name}_th{side}", R * 0.05, hip_z * 0.55, (0, 0, 0), ink()); parent(th, hp, keep=False); th.location = (0, 0, -hip_z * 0.275)
                kn = empty(f"{name}_kn{side}", (0, 0, -hip_z * 0.55), hp)
                sh_ = cyl(f"{name}_shin{side}", R * 0.05, hip_z * 0.5, (0, 0, 0), ink()); parent(sh_, kn, keep=False); sh_.location = (0, 0, -hip_z * 0.25)
                self.leg[side] = (hp, kn)
        # body
        self.body = sphere(f"{name}_body", 1, (0, 0, 0), toon(st["body"]), scale=(R * 0.62, R * 0.5, body_h * 0.56), ol=OLW / 0.6)
        parent(self.body, self.root, keep=False); self.body.location = (0, 0, self.body_z)
        # decals on body front
        front_y = -R * 0.5
        if st.get("tag"):
            t = plane(f"{name}_tag", R * 0.42, R * 0.13, (0, 0, 0), (math.pi / 2, 0, 0), flat(st["tag"]))
            parent(t, self.root, keep=False); t.location = (R * 0.2, front_y - 0.004, self.body_z + R * 0.25)
        if st.get("badge"):
            b = plane(f"{name}_badge", R * 0.16, R * 0.16, (0, 0, 0), (math.pi / 2, 0, 0), flat("fishlogo.png", alpha=True))
            parent(b, self.root, keep=False); b.location = (-R * 0.24, front_y - 0.004, self.body_z + R * 0.25)
        if st.get("tie"):
            tie = box(f"{name}_tie", (R * 0.1, R * 0.02, R * 0.6), (0, 0, 0), toon(st["tie"]), ol=OLW * 0.6)
            parent(tie, self.root, keep=False); tie.location = (0, front_y - 0.01, self.body_z + R * 0.2)
        if st.get("badgegold"):
            bg = cyl(f"{name}_gold", R * 0.08, R * 0.02, (0, 0, 0), toon((240, 200, 60)), rot=(math.pi / 2, 0, 0), ol=OLW * 0.5)
            parent(bg, self.root, keep=False); bg.location = (R * 0.25, front_y - 0.01, self.body_z - R * 0.2)
        if st.get("chain"):
            for k in range(9):
                a = math.pi * (0.15 + 0.7 * k / 8)
                s = sphere(f"{name}_ch{k}", R * 0.035, (0, 0, 0), toon((240, 200, 60)), segs=8)
                parent(s, self.root, keep=False)
                s.location = (math.cos(a) * R * 0.32, front_y + 0.02 + math.sin(a) * 0.0, self.body_z + body_h * 0.42 - math.sin(a) * R * 0.25)
        # arms: shoulder empties so poses are rotations
        self.arm = {}
        for side, sx in (("L", 1), ("R", -1)):
            sh = empty(f"{name}_sh{side}", (sx * R * 0.5, 0, neck_z - R * 0.25), self.root)
            up = cyl(f"{name}_ua{side}", R * 0.045, R * 0.75, (0, 0, -R * 0.375), ink()); parent(up, sh, keep=False); up.location = (0, 0, -R * 0.375)
            el = empty(f"{name}_el{side}", (0, 0, -R * 0.75), sh)
            lo = cyl(f"{name}_la{side}", R * 0.045, R * 0.7, (0, 0, -R * 0.35), ink()); parent(lo, el, keep=False); lo.location = (0, 0, -R * 0.35)
            hand = sphere(f"{name}_hand{side}", R * 0.1, (0, 0, 0), ink(), segs=16); parent(hand, el, keep=False); hand.location = (0, 0, -R * 0.72)
            self.arm[side] = (sh, el, hand)
        # head
        self.head = empty(f"{name}_head", (0, 0, head_z), self.root)
        skin = (246, 244, 240) if not back else (110, 70, 40)
        if back and kind.startswith("kyle"):
            skin = st["hair"]
        hs = sphere(f"{name}_skull", R, (0, 0, 0), toon(skin, soft=0.55), ol=OLW)
        parent(hs, self.head, keep=False); hs.location = (0, 0, 0)
        if st.get("hair") and not back:
            self._hair(st["hair"], R, OLW, tuft=st.get("tuft"))
        elif back and st.get("tuft"):
            self._tuft(st["hair"], R, OLW)
        if st.get("hat") == "bucket":
            self._bucket(R, OLW)
        elif st.get("hat") == "cop":
            cap = sphere(f"{name}_cap", R * 0.92, (0, 0, 0), toon((36, 50, 92)), scale=(1, 1, 0.55), ol=OLW)
            parent(cap, self.head, keep=False); cap.location = (0, 0, R * 0.6)
            vis = cyl(f"{name}_visor", R * 0.95, R * 0.08, (0, 0, 0), toon((24, 30, 60)), ol=OLW * 0.7)
            parent(vis, self.head, keep=False); vis.location = (0, -R * 0.1, R * 0.45); vis.scale = (1, 1.1, 1)
        if st.get("curls"):
            import random
            rr = random.Random(hash(name) & 0xffff)
            for k in range(30):
                a = rr.uniform(0, 2 * math.pi); b = rr.uniform(-0.2, 1.2)
                pos = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b) * 0.9 + 0.15, math.sin(b))) * R
                if pos.y < -R * 0.55 and pos.z < R * 0.6:
                    continue
                cu = sphere(f"{name}_curl{k}", R * 0.28, (0, 0, 0), toon(st["curls"]), segs=16, ol=OLW * 0.6)
                parent(cu, self.head, keep=False); cu.location = pos
        # face decals (one plane per expression; toggled via hide_render)
        self.faces = {}
        if not back:
            for f in faces:
                fp = plane(f"{name}_face_{f}", R * 1.75, R * 1.75, (0, 0, 0), (math.pi / 2, 0, 0), flat(f"face_{f}.png", alpha=True))
                parent(fp, self.head, keep=False); fp.location = (0, -R * 0.93, -R * 0.02)
                self.faces[f] = fp
            self.set_face(faces[0], 1)
        self.pose("idle", 1)

    # ---- parts
    def _hair(self, col, R, OLW, tuft=True):
        hs = sphere(f"{self.name}_hair", R * 1.035, (0, 0, 0), toon(col, soft=0.5), ol=OLW)
        bm = bmesh.new(); bm.from_mesh(hs.data)
        kill = [v for v in bm.verts if v.co.z < R * 0.18 + 0.35 * R * max(0, -v.co.y / R) * 0 and not (v.co.y > 0 and v.co.z > -R * 0.5)]
        # fringe: cut lower at the back/sides, higher at the front with a slight wave
        kill = []
        for v in bm.verts:
            ang = math.atan2(v.co.x, -v.co.y)
            front = max(0.0, math.cos(ang))
            cut = R * 0.22 * front - R * 0.32 * (1 - front)
            if v.co.z < cut:
                kill.append(v)
        bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(hs.data); bm.free()
        parent(hs, self.head, keep=False); hs.location = (0, 0.0, 0)
        if tuft:
            self._tuft(col, R, OLW)

    def _tuft(self, col, R, OLW):
        cu = bpy.data.curves.new(f"{self.name}_tuftc", "CURVE"); cu.dimensions = "3D"
        cu.bevel_depth = R * 0.13; cu.bevel_resolution = 4; cu.use_fill_caps = True
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(2)
        pts = [((0, 0, R * 0.85), 1.0), ((R * 0.02, 0, R * 1.3), 0.6), ((R * 0.3, 0, R * 1.55), 0.05)]
        for bp, (co, rad) in zip(sp.bezier_points, pts):
            bp.co = co; bp.radius = rad; bp.handle_left_type = bp.handle_right_type = "AUTO"
        t = bpy.data.objects.new(f"{self.name}_tuft", cu); bpy.context.collection.objects.link(t)
        t.data.materials.append(toon(col))
        parent(t, self.head, keep=False); t.location = (0, 0, 0)
        # ink outline: a slightly fatter black copy behind
        cu2 = cu.copy(); cu2.bevel_depth = R * 0.13 + OLW * 0.35; cu2.materials.clear(); cu2.materials.append(ink())
        t2 = bpy.data.objects.new(f"{self.name}_tuft_ol", cu2); bpy.context.collection.objects.link(t2)
        parent(t2, self.head, keep=False); t2.location = (0, R * 0.01, 0)

    def _bucket(self, R, OLW):
        crown = cyl(f"{self.name}_crown", R * 0.78, R * 0.55, (0, 0, 0), toon((122, 128, 56)), ol=OLW)
        parent(crown, self.head, keep=False); crown.location = (0, 0, R * 0.72); crown.scale = (1, 1, 1)
        brim = cyl(f"{self.name}_brim", R * 1.18, R * 0.06, (0, 0, 0), toon((108, 114, 48)), ol=OLW)
        parent(brim, self.head, keep=False); brim.location = (0, 0, R * 0.45); brim.rotation_euler = (math.radians(-8), 0, 0)
        for k, col in enumerate([(230, 80, 80), (80, 170, 220), (240, 200, 60), (230, 120, 200)]):
            a = math.radians(-120 + k * 55)
            lu = sphere(f"{self.name}_lure{k}", R * 0.1, (0, 0, 0), toon(col), scale=(1.6, 0.7, 0.7), segs=12, ol=OLW * 0.5)
            parent(lu, self.head, keep=False); lu.location = (math.sin(a) * R * 0.8, -math.cos(a) * R * 0.8, R * 0.78)

    # ---- animation
    POSES = {  # (shoulder pitch, shoulder roll, elbow pitch) per side, degrees
        "idle": ((8, 14, -12), (8, -14, -12)),
        "shrug": ((10, 70, -100), (10, -70, -100)),
        "arms_up": ((0, 150, -15), (0, -150, -15)),
        "hold": ((50, 10, -85), (8, -14, -12)),
        "hold_up": ((70, 25, -110), (8, -14, -12)),
        "both_forward": ((60, 8, -50), (60, -8, -50)),
        "wave": ((8, 14, -12), (0, -150, 30)),
        "wheel": ((55, 25, -40), (55, -25, -40)),
        "down": ((-160, 10, 0), (-160, -10, 0)),
        "sit": ((40, 12, -60), (40, -12, -60)),
    }

    def pose(self, name, frame, interp="BEZIER"):
        p = self.POSES[name]
        for (side, (pitch, roll, elb)) in zip(("L", "R"), p):
            sh, el, _ = self.arm[side]
            sh.rotation_euler = (math.radians(pitch), math.radians(roll), 0)
            el.rotation_euler = (math.radians(elb), 0, 0)
            sh.keyframe_insert("rotation_euler", frame=frame); el.keyframe_insert("rotation_euler", frame=frame)

    def legs_pose(self, frame, hipL=0, kneeL=0, hipR=0, kneeR=0):
        for side, h, k in (("L", hipL, kneeL), ("R", hipR, kneeR)):
            if side not in self.leg:
                continue
            hp, kn = self.leg[side]
            hp.rotation_euler = (math.radians(h), 0, 0); kn.rotation_euler = (math.radians(k), 0, 0)
            hp.keyframe_insert("rotation_euler", frame=frame); kn.keyframe_insert("rotation_euler", frame=frame)

    def sit(self, frame):
        self.legs_pose(frame, -85, 85, -85, 85)

    def walk(self, f0, f1, step=10, swing=28):
        """Leg + arm swing between frames f0..f1 (root motion is animated separately with move())."""
        f, s = f0, 1
        while f <= f1:
            self.legs_pose(f, swing * s, 8 if s > 0 else 25, -swing * s, 25 if s > 0 else 8)
            for side, sgn in (("L", -s), ("R", s)):
                sh, el, _ = self.arm[side]
                sh.rotation_euler = (math.radians(20 * sgn), math.radians(12 if side == "L" else -12), 0)
                sh.keyframe_insert("rotation_euler", frame=f)
            f += step; s = -s

    def set_face(self, f, frame):
        for k, o in self.faces.items():
            o.hide_render = (k != f); o.hide_viewport = (k != f)
            o.keyframe_insert("hide_render", frame=frame); o.keyframe_insert("hide_viewport", frame=frame)

    def move(self, frame, loc=None, rot_z=None, scale=None):
        if loc is not None:
            self.root.location = loc; self.root.keyframe_insert("location", frame=frame)
        if rot_z is not None:
            self.root.rotation_euler = (0, 0, rot_z); self.root.keyframe_insert("rotation_euler", frame=frame)
        if scale is not None:
            self.root.scale = (scale,) * 3; self.root.keyframe_insert("scale", frame=frame)

    def bob(self, frames, amp=0.01, period=36):
        """Idle life: head bob + body breathe over the whole shot."""
        for f in range(1, frames + 1, 6):
            ph = 2 * math.pi * f / period
            self.head.location.z = self.head_z + math.sin(ph) * amp
            self.head.rotation_euler = (0, math.sin(ph * 0.5) * 0.03, 0)
            self.head.keyframe_insert("location", frame=f); self.head.keyframe_insert("rotation_euler", frame=f)
            self.body.scale.z = self.body.scale.z  # placeholder to keep API symmetric


# ------------------------------------------------------------------ camera
def camera(loc, look, lens=28, dof_obj=None, fstop=2.8):
    cd = bpy.data.cameras.new("Cam"); cd.lens = lens; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 24
    cam = bpy.data.objects.new("Cam", cd); bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    tgt = empty("CamTarget", look)
    tr = cam.constraints.new("TRACK_TO"); tr.target = tgt; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
    cam.location = loc
    if dof_obj is not None:
        cd.dof.use_dof = True; cd.dof.focus_object = dof_obj; cd.dof.aperture_fstop = fstop
    return cam, tgt


def key_cam(cam, tgt, frame, loc=None, look=None, lens=None):
    if loc is not None:
        cam.location = loc; cam.keyframe_insert("location", frame=frame)
    if look is not None:
        tgt.location = look; tgt.keyframe_insert("location", frame=frame)
    if lens is not None:
        cam.data.lens = lens; cam.data.keyframe_insert("lens", frame=frame)


def render(out_dir, frames=None):
    sc = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    sc.render.filepath = os.path.join(out_dir, "f_")
    if frames:
        sc.frame_start, sc.frame_end = frames
    bpy.ops.render.render(animation=True)


def still(path, frame=1):
    sc = bpy.context.scene; sc.frame_set(frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
