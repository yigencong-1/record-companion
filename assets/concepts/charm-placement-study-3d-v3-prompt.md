# 挂件承接方案：三维结构重绘记录

日期：2026-10-08。按用户澄清，大唱片始终平放，仅比较小挂件平放浅座与插槽。此版本先用 Three.js 几何占位图固定相对位置，再交给上游图像模型改善材质和光照。

最终图：[结构重绘图](charm-placement-study-3d-v3.png)。模型为上游 `gpt-image-2.5-sunburst`，请求类型为 `edit`，输入为本目录之外的几何参考截图；实际返回 PNG 为 1448×1086 RGB。图像用于结构关系和外观审阅，不是制造 CAD、尺寸证明或装配验证。

## 公开提示词

```text
Use the attached geometrically consistent four-panel 3D reference as the layout authority. Create one clean industrial design 3D diagram, 2 columns and 2 rows. Preserve the reference camera, object positions, proportions, front orientation and component count. Improve materials, antialiasing, fabric texture, realistic soft light and detailed speaker cones. Do not redesign or rearrange the structure.

Top left: small record keychain lies FLAT in a fixed shallow dock. Top right: the same SMALL keychain record stands upright in a shallow fixed SLOT. BOTH devices have one LARGE horizontal black record on a horizontal rotating platter. No upright large record, no tonearm. The small dock is separate at the rear-right and does not touch the large platter. Its solid supporting roof remains sealed below it; the slot does not penetrate the acoustic chamber.

Bottom left and bottom right: exact same respective devices, exact same positions, with only the front half of the top cover and the two front speaker grille covers removed for inspection. The existing full-height front baffles stay. There are EXACTLY TWO loudspeaker drivers per device, one on each FRONT end; each driver is directly behind the corresponding top-row grille at the same center height. No extra lower grilles, no speaker stacked above a grille, no upward-facing speaker. Each driver's back opens into its own closed left or right chamber. Solid vertical partitions isolate the center electronics bay. The cutaway convention exposes the front half of these chambers only; the retained rear roof supports the small keychain dock.

Keep the SAME flat blue rectangular battery low in the central bay in both lower views, with a green PCB on standoffs above it, and the metal platter motor support bridge above the PCB. The battery is partly occluded by the board and front panel; preserve this occlusion rather than moving it to make it visible. Keep clear vertical separation without intersection. Front center controls stay in the same place in all four panels: one rectangular display to the left, one silver pushable rotary knob to the right of the display, exactly two small round buttons vertically beside the knob. No extra controls, decorations or invented compartments. The front baffles meet the side walls, floor and roof without unintended open gaps.

Render neutral light-gray shell, dark-gray grille cloth, black record, muted gold labels/dock, green board, blue battery. Bright plain near-white background. Crisp readable technical illustration with restrained realism, all four objects fully framed. Keep the reference's panel arrangement. Use these concise Chinese headings: top left "A 小挂件平放浅座", top right "B 小挂件插槽", lower left "A 对应剖视", lower right "B 对应剖视". Add brief clear Chinese labels "左前出声" and "右前出声" outside the top-left object with thin leader lines pointing to its actual front grilles. Footer: "结构概念示意 · 非比例 · 器件与尺寸待定". Do not add dimensions, logos, photorealistic environments or extra technical claims. Geometry and corresponding-view consistency are the priority.
```

## 检查结果

- 上排和下排的左右格栅/扬声器共用同一前障板位置，剖视只露出其后的对应单元。
- 两个独立音腔由实体隔板与中央电路区分开；蓝色扁平电池和绿色 PCB 在两个剖视中保持一致。
- 大唱片四个视图均水平；左列挂件平放在浅座，右列挂件插入固定槽；挂件承接区与转盘分开。
- 图中“左前出声”“右前出声”指向正面两侧格栅，表示左右声道从这里向前辐射。
