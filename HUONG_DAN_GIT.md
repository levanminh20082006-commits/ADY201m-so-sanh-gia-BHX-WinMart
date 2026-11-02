# Hướng dẫn làm việc nhóm trên Git

Quy tắc chung: **không ai đẩy thẳng vào `main`**. Mỗi việc làm trên một nhánh riêng → mở Pull Request → trưởng nhóm duyệt → gộp vào `main`.

## 1. Chuẩn bị (làm 1 lần)

1. Tạo tài khoản GitHub và chấp nhận lời mời vào kho (email mời từ GitHub, hoặc vào trang kho bấm **Accept invitation**).
2. Cài Git: https://git-scm.com/download/win (bấm Next đến hết).
3. Khai báo tên và email — **email phải trùng email tài khoản GitHub của chính bạn**:

```powershell
git config --global user.name "Họ Tên Của Bạn"
git config --global user.email "email-github-cua-ban@gmail.com"
```

4. Lấy project về máy:

```powershell
git clone https://github.com/<chu-kho>/<ten-kho>.git
cd <ten-kho>
```

## 2. Mỗi lần nhận một việc (Issue)

```powershell
git checkout main
git pull                                  # lấy bản mới nhất
git checkout -b ten-ban/ten-viec          # ví dụ: lan/readme-tu-dien-du-lieu
```

Làm việc, lưu file, rồi:

```powershell
git status                                # xem đã sửa những file nào
git add <file-da-sua>
git commit -m "Mô tả ngắn việc đã làm (#số-issue)"
git push -u origin ten-ban/ten-viec
```

Commit nhỏ, mỗi commit một ý, viết rõ đã làm gì. Ghi `#số-issue` để GitHub tự liên kết với việc được giao.

## 3. Mở Pull Request

1. Vào trang kho trên GitHub, bấm **Compare & pull request**.
2. Tiêu đề: việc đã làm. Nội dung: làm gì, kiểm tra thế nào, ghi `Closes #số-issue`.
3. Chọn **Reviewers** là trưởng nhóm, bấm **Create pull request**.
4. Nếu được yêu cầu sửa: sửa trên cùng nhánh, `commit` rồi `push` lại — Pull Request tự cập nhật.

## 4. Sau khi Pull Request được gộp

```powershell
git checkout main
git pull
git branch -d ten-ban/ten-viec
```

## 5. Trước khi mở Pull Request có sửa code

```powershell
.\.venv\Scripts\python.exe -m pytest      # tất cả test phải đạt
```

## Lưu ý

- Không đưa lên Git: thư mục `.venv`, file `.env`, mật khẩu, file tạm (đã có sẵn trong `.gitignore`).
- Không sửa trực tiếp dữ liệu gốc trong `data/raw_py/`.
- Gặp xung đột (conflict) khi `git pull`: báo trưởng nhóm, không tự xóa phần code của người khác.
