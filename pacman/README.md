# Pacman Task 2.1 – Detailed Documentation

Tài liệu này giải thích cấu trúc thư mục `pacman/`, nhiệm vụ cụ thể của từng file/hàm/chức năng, đồng thời đánh giá mức độ đáp ứng các yêu cầu của Task 2.1 (mục 2.1.(1), (2), (5), (7)).

## 1. Kiến trúc tổng quan

```
pacman/
├── __init__.py
├── environment.py
├── heuristics.py
├── auto.py
├── main.py
└── layouts/
    ├── medium_layout.txt
    └── assignment_layout.txt
puzzle/
└── search.py
```

`puzzle/search.py` chứa bộ khung A* tái sử dụng từ Task 1. Thư mục `pacman/` xây dựng bài toán Pacman dựa trên bộ khung này.

## 2. Mô tả chi tiết từng module

### 2.1. `puzzle/search.py` – Thuật toán chung 

* `Action(type, pos1=None, pos2=None, payload=None)`: cấu trúc mô tả hành động kèm thông tin bổ sung.
* `Node`: lưu trữ `state`, `parent`, `action`, `path_cost`, `heuristic`; cung cấp `f_score` và `get_path()`.
* `Problem`: interface trừu tượng với `initial_state`, `is_goal(state)`, `get_successors(state)`.
* `Heuristic`: interface với `calculate(state)`.
* `AStar`: cài đặt A* tiêu chuẩn (frontier dạng heap, closed set, cập nhật khi tìm thấy đường tốt hơn). Được Pacman import lại mà không chỉnh sửa.

### 2.2. `pacman/environment.py` – Mô hình state-space

#### Kiểu dữ liệu

* `Point = Tuple[int, int]`: toạ độ (row, col).
* `GhostState(position: Point, direction: int)`: 1 ma, `direction` = ±1 theo trục ngang.
* `PacmanState`:
  - `pacman_pos`: vị trí Pacman.
  - `food`, `pies`: `frozenset[Point]` – các ô chưa ăn.
  - `ghosts`: tuple `GhostState`.
  - `pie_timer`: số bước xuyên tường còn lại (5 sau khi ăn pie).
  - `time_step`: tổng số bước đã đi (để kích hoạt quay).
  - `layout_index`: 0–3, dùng layout quay tương ứng.
* `PacmanLayout`:
  - `width`, `height`.
  - `walls`, `food`, `pies`: tập các ô.
  - `teleports`: dict tên góc (`TL`, `TR`, `BL`, `BR`) → toạ độ.
  - `exit_gate`, `pacman_start`.
  - `ghost_starts`: tuple `GhostState`.
  - Methods: `in_bounds(pos)`, `is_wall(pos)`, `corner_name(pos)`.

#### `PacmanEnvironment`

* `_parse_layout(lines)`: đọc file ký tự `%` `.` `O` `G` `P` `E` thành `PacmanLayout`.
* `_rotate_layout(layout)`: tạo layout quay 90° (quay toàn bộ tường, food, pie, teleport, start, exit, ghost).
* Constructor:
  - Sinh 4 layout quay (0–3) lưu trong `self.layouts`.
  - Thiết lập `initial_state` với dữ liệu layout 0, `pie_timer=0`, `time_step=0`, `layout_index=0`.
* `rotate_state(state)`: xoay trạng thái sang layout kế tiếp khi `time_step % 30 == 0`. Tất cả toạ độ (Pacman, food, pie, ma) được biến đổi; ma khởi động lại với hướng +1.

#### `PacmanProblem(Problem)`

* `MOVE_DELTAS`: map 5 hành động `{"Up", "Down", "Left", "Right", "Stay"}` → vector dịch chuyển. `Stay` cho phép đứng yên.
* `is_goal(state)`: true khi `state.food` rỗng và Pacman ở `exit_gate` của layout hiện tại.
* `get_successors(state)`:
  1. Duyệt mọi action trong `MOVE_DELTAS`, gọi `_apply_move`.
  2. Nếu Pacman đang ở góc (`corner_name` khác `None`), thử teleport tới các góc khác qua `_apply_teleport`.
* `_apply_move(state, layout, move_name, delta)`:
  - Tính vị trí mới, kiểm tra biên và tường; chỉ cho xuyên tường khi `pie_timer > 0`.
  - Không cho bước vào ô đang có ma; nếu ăn pie thì `pie_timer = 5`.
  - Cập nhật `food`/`pies` (xoá ô đã ăn).
  - Ma di chuyển ngang bằng `_move_ghost`. Nếu ma mới đè lên Pacman → bỏ trạng thái.
  - Giảm `pie_timer` (trừ khi hành động `Stay`), tăng `time_step`.
  - Nếu `time_step % PacmanEnvironment.ROTATION_PERIOD == 0` (30 bước) → `rotate_state`.
  - Trả `[(new_state, Action(move_name), 1)]`.
* `_apply_teleport(state, layout, target)`:
  - Teleport từ góc hiện tại tới `target`, kiểm tra ma/tường/pie/food tương tự `_apply_move`.
  - Cập nhật ma, timer, rotation y như trên.
* `_move_ghost(ghost, layout)`:
  - Di chuyển một bước theo `direction` (±1 trên cột). Nếu gặp tường/ra ngoài → đảo chiều và thử bước ngược lại. Nếu bị kẹt hai phía → đứng yên.

### 2.3. `pacman/heuristics.py` – Heuristic cho A* 

Các heuristic được xây dựng nhằm đối chiếu giữa độ chính xác và chi phí tính toán:

1. **`PieAwareHeuristic`**  
   * `_distance` dùng teleport-adjusted Manhattan (không xét tường) có cache.  
   * `calculate`: lấy khoảng cách nhỏ nhất tới food, giảm giá trị khi Pacman đang có pie, cộng lợi ích nếu pie gần.  
   * Rất nhẹ, phù hợp làm baseline/so sánh với dự án mẫu; admissible & consistent vì luôn là cận dưới.

2. **`FoodMSTHeuristic`**  
   * Cache BFS bỏ tường (có teleport) để lấy cạnh cận dưới.  
   * Tính chi phí cây khung nhỏ nhất trên `food ∪ {exit}` theo cạnh này.  
   * Mạnh hơn `PieAware` nhưng vẫn rẻ; admissible & consistent vì sử dụng metric cận dưới.

3. **`ExactDistanceHeuristic`**  
   * Precompute BFS thật (có tường + teleport) cho mọi ô passable.  
   * Kết hợp ba cận dưới: `H_far` (food xa nhất), `H_mst` (`minDist + MST`), `H_diam` (đường kính food) bằng `max`.  
   * Nếu `pie_timer > 0` trả 0 để tránh đánh giá quá cao vì BFS không xét xuyên tường. Dùng khi cần tham chiếu heuristic chính xác.

4. **`ExactMSTHeuristic`** *(H₁ – mặc định khi chạy CLI)*  
   * Thêm metric “free” (bỏ tường) bên cạnh metric thật.  
   * Với mỗi metric, tính `minDist + MST`; trả `min(h_exact, h_free)`.  
   * Giữ admissibility/consistency kể cả khi Pacman ăn pie → đây là heuristic khuyến nghị cho bài nộp.

5. **`CombinedHeuristic`**  
   * Lấy `max` của bốn heuristic trên để benchmark mạnh nhất.  
   * Chi phí tính toán cao hơn; chỉ dùng khi so sánh heuristic hoặc layout đặc biệt lớn.

Nhờ có nhiều heuristic, bạn có thể trình bày phần phân tích: từ baseline (PieAware), heuristic MST kinh điển, đến phiên bản chính xác (Exact/ExactMST) và bản tổng hợp (Combined). CLI mặc định dùng chế độ `auto`, tự động chọn giữa `ExactMST` và `Combined` dựa trên độ phức tạp layout.
* `__all__` liệt kê các heuristic để import ngoài.

### 2.4. `pacman/auto.py`

* `_select_heuristic(name, environment)`:
  - Ánh xạ tên/alias (`exact`, `exact-mst`, `exact-dist`, `pie`, `mst`, `combo`, …) tới lớp heuristic.
  - Khởi tạo heuristic với `environment`.
* `run_auto_mode(layout_lines, heuristic="auto")`:
  1. Tạo `PacmanEnvironment`.
  2. Gói thành `PacmanProblem`.
  3. Chọn heuristic qua `_select_heuristic`.
  4. Chạy `AStar(problem, heuristic)` và trả `(path, cost, expanded, frontier_max)`.

### 2.5. `pacman/main.py`

CLI nội bộ – chạy bằng `python -m pacman.main`. Tham số:

* `--layout <path>`: layout `.txt` (mặc định dùng layout nhỏ dựng sẵn).
* `--heuristic` (mặc định `auto`): chấp nhận alias theo `_select_heuristic`.

In ra chuỗi action (`Up/Down/Left/Right/Stay`), chi phí, số nút mở rộng, frontier tối đa.

### 2.6. `pacman/layouts/*.txt`

* `small_basic.txt`: layout nhỏ, ít food/ghost – dùng kiểm thử nhanh.
* `medium_twists.txt`: mê cung trung bình với đường ngoằn ngoèo, 1 ghost và 1 pie.
* `large_multi_pie.txt`: layout lớn có nhiều pie/ghost để stress-test.
* `maze.txt`: layout phức tạp theo đề gốc (nhiều food, teleport, ghost) – so sánh với dự án tham khảo.

## 3. Cách chạy & kiểm thử

1. **Demo nhanh** (layout nhỏ, để chế độ auto):
   ```bash
   python -m pacman.main
   ```
2. **Chạy layout cụ thể** (tùy chọn ghi đè heuristic):
   ```bash
   python -m pacman.main --layout pacman/layouts/medium_twists.txt
   python -m pacman.main --layout pacman/layouts/maze.txt --heuristic combo
   ```
3. **Đổi heuristic thủ công (nếu cần phân tích)**:
   - `auto`/`dynamic`: để hệ thống chọn giữa `ExactMST` và `Combined`.
   - `exact`/`exact-mst`/`shortest` (`ExactMSTHeuristic`).
   - `exact-dist` (`ExactDistanceHeuristic`).
   - `pie` (`PieAwareHeuristic`).
   - `mst` (`FoodMSTHeuristic`).
   - `combo` (`CombinedHeuristic` – mạnh nhưng tính toán nặng hơn).

*Lưu ý*: chế độ `auto` sẽ chọn `ExactMST` cho layout nhỏ/vừa và `Combined` cho layout phức tạp (nhiều food/ghost hoặc kích thước lớn). Bạn vẫn có thể chỉ định thủ công nếu muốn so sánh.
