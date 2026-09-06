from pathlib import Path
from PIL import Image, ImageDraw
from photo_filter.services.visual_matcher import (
    VisualMatchWorker,
    get_image_hash,
)


def test_get_image_hash_identical_images(tmp_path: Path) -> None:
    img1_path = tmp_path / "img1.jpg"
    img2_path = tmp_path / "img2.jpg"

    im1 = Image.new("RGB", (200, 200), color="white")
    d1 = ImageDraw.Draw(im1)
    d1.rectangle([20, 20, 100, 100], fill="blue")
    im1.save(img1_path)

    # Save same image as JPG
    im1.save(img2_path)

    h1 = get_image_hash(img1_path)
    h2 = get_image_hash(img2_path)

    assert (h1 - h2) == 0


def test_visual_match_worker_execution(tmp_path: Path) -> None:
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    dest_dir = tmp_path / "output"
    dest_dir.mkdir()

    # Create original photo 1 (Blue square)
    raw_photo = src_dir / "DSC01234.JPG"
    im1 = Image.new("RGB", (200, 200), color="white")
    d1 = ImageDraw.Draw(im1)
    d1.rectangle([20, 20, 100, 100], fill="blue")
    im1.save(raw_photo)

    # Create original photo 2 (Red circle)
    other_photo = src_dir / "DSC09999.JPG"
    im2 = Image.new("RGB", (200, 200), color="black")
    d2 = ImageDraw.Draw(im2)
    d2.ellipse([50, 50, 150, 150], fill="red")
    im2.save(other_photo)

    # Client screenshot of photo 1 (resized slightly or compressed)
    client_screenshot = samples_dir / "screenshot_zalo_1.png"
    im1.resize((150, 150)).save(client_screenshot)

    # Completely different sample (Yellow stars / triangles)
    unmatched_screenshot = samples_dir / "screenshot_random.png"
    im3 = Image.new("RGB", (200, 200), color="green")
    d3 = ImageDraw.Draw(im3)
    d3.polygon([(10, 10), (190, 50), (100, 190)], fill="yellow")
    im3.save(unmatched_screenshot)

    worker = VisualMatchWorker(
        sample_paths=[client_screenshot, unmatched_screenshot],
        source_dir=src_dir,
        destination_dir=dest_dir,
        threshold=10,
    )

    result_items = []
    found_count = 0
    not_found_count = 0

    def on_finished(items, f_cnt, nf_cnt):
        nonlocal result_items, found_count, not_found_count
        result_items = items
        found_count = f_cnt
        not_found_count = nf_cnt

    worker.finished.connect(on_finished)
    worker.run()

    assert found_count == 1
    assert not_found_count == 1
    assert (dest_dir / "ẢNH CHỌN RAW" / "DSC01234.JPG").exists()
    assert (dest_dir / "ẢNH CHƯA TÌM THẤY" / "screenshot_random.png").exists()
