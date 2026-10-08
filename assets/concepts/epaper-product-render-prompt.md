# 墨水屏唱片桌搭：实体效果图提示词

日期：2026-10-08。用途：生成可审阅的3D产品效果图。图像表达外观与操作位置，不作为制造尺寸、音腔或装配验证。配色只是本次中性外观探索。

本文件为公开复现提示词，已按通用唱片桌搭定位清理；原图未重新生成。见[实体效果图](epaper-player-3d.png)和[V005](../../product/validation.md#v0052026-10-08-墨水屏复用ap配网与实体效果图)。

原生成参数：模型名gpt-image-2，单张，medium，请求1536×1024；返回PNG实际为1672×941，已查看。图中格栅的转角范围及两视角细节仍需结构细化，不能据此确定扬声器数量或音腔。几何尺寸、配色和材质均未定。

## 公开复现提示词

Use case: product-mockup
Asset type: 3D physical product concept for a compact desktop music player
Primary request: A realistic industrial-design render of one compact horizontal desktop music player with left and right speakers, a front e-paper display, and record-themed interaction on the top.
Scene/backdrop: Clean neutral studio surface and background, soft daylight and natural contact shadows. Show the object as a tangible product, with realistic seams, wall thickness and feet.
Subject: A small low rectangular enclosure in the approximate 15-centimeter width class; proportions are exploratory, not manufacturing dimensions. The front face has a recessed wide 2.9-inch-class monochrome e-paper panel, with a display aspect ratio about 296:128. A small rotary control is beside the display. Each side face has one acoustically open speaker grille, with space implied for a separate left and right speaker enclosure. The top has a larger decorative black record on a supported rotating platter, and a separate shallow stationary cradle holding a smaller record-shaped bag charm with a short closed attachment loop. The charm and its loop must be physically clear of the large platter. The music is stored in the main body; the charm is a passive identification accessory. An internal battery is implied by the enclosure and a rear USB-C charging connector; no exposed battery or visible wiring.
Style/medium: Photorealistic 3D CAD-style product render with restrained, plausible industrial design. Neutral matte enclosure, charcoal speaker fabric or perforated grille, tactile rotary control, subtle material texture.
Composition/framing: One wide image containing a large front-left three-quarter view and a smaller rear-right three-quarter view of the exact same object, so the front e-paper, top platter, stationary charm cradle, both side speaker grilles and rear USB-C connector can all be inspected. Keep geometry and materials identical between views.
Lighting/mood: Soft clear studio lighting, believable reflections on plastic, diffuse e-paper surface with no emitted glow.
Text (verbatim): Only "09:41" on the e-paper, with simple monochrome calendar, music and battery icons. No other text.
Constraints: Compact horizontal desktop form; true physical side speaker apertures; monochrome reflective e-paper, not a luminous LCD; larger platter and smaller stationary charm have distinct roles; complete object visible; realistic construction; no logo, no dimensions, no watermark.
Avoid: Tonearm, gramophone horn, external antenna, touchscreen gestures, exposed electronics, invented microphone features, neon lighting, floating parts, inconsistent views, large furniture-scale object.
