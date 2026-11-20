# Quy trình đóng góp

1. Mỗi việc có một dòng trong `docs/M4/project_board.csv` (owner, deadline, trạng thái To Do / In Progress / Blocked / Review / Done, reviewer).
2. Nhánh `m<N>/<chu-de>`, commit nhỏ, nội dung tách khỏi thay đổi định dạng (CRLF).
3. Chỉ chủ sở hữu số liệu mới sửa số liệu: M1 dữ liệu; M2 K-Means/DBSCAN; M3 HDBSCAN/temporal. M4 chỉ hợp nhất, vẽ và kiểm tra; nếu thấy lệch thì mở issue/ghi vào `docs/M4/m4-handoff-discrepancies.md`.
4. Mọi chạy chính thức: ghi `run_id`, `sample_id`, tham số vào `outputs/metrics/run_log.csv`. Không ghi đè phát hành cũ; đổi dữ liệu thì tăng phiên bản.
5. Trước khi bàn giao: `python -m pytest -q tests`, `python scripts/run_qa.py`, `python scripts/check_repo.py`.
6. "Done" = file mở được + owner giải thích được + một thành viên khác đã review (BA 3.8).
7. Không commit `data/`, `outputs/labels/`, khóa/secret, đường dẫn tuyệt đối cá nhân.
Quy ước đặt tên: `docs/M4/artifact_naming.md`; style hình: `docs/M4/visual_style_guide.md`.
