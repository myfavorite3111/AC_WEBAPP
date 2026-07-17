import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VP = ROOT / "marketing-assets" / "video-production"
RAW = VP / "raw-recordings"
CARDS = VP / "title-cards"
THUMBS = VP / "thumbnails"
EXPORTS = VP / "exports"
for path in (RAW, CARDS, THUMBS, EXPORTS):
    path.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "puriaccooling.settings")
sys.path.insert(0, str(ROOT))

import django
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

django.setup()

from customers.models import Customer
from service.models import ServiceComplaint
from projects.models import CustomerProject
from boq.models import ProjectBOQ
from material_issue.models import MaterialIssue
from store.models import StoreItem, StoreTransaction
from amc.models import AMCContract

PYTHON = str(ROOT / "venv" / "bin" / "python")
BASE_URL = "http://127.0.0.1:8000"
W, H = 1920, 1080
FPS = 30
OPENING = 4.0
CLOSING = 5.0
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"


def run(cmd, **kwargs):
    print("RUN", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True, cwd=ROOT, **kwargs)


def reset_data():
    run([PYTHON, "manage.py", "reset_demo_data"])


def start_server():
    proc = subprocess.Popen(
        [PYTHON, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            subprocess.run(["curl", "-fsS", BASE_URL + "/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return proc
        except subprocess.CalledProcessError:
            time.sleep(0.5)
    raise RuntimeError("Server did not start")


def stop_server(proc):
    if not proc:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass


def get_records():
    customer = Customer.objects.get(customer_name="Northstar Business Park")
    service = ServiceComplaint.objects.get(customer=customer, nature_of_complaint__icontains="Server room")
    project = CustomerProject.objects.get(site_name="VRV retrofit - Block A")
    boq = ProjectBOQ.objects.get(project=project)
    issue = MaterialIssue.objects.get(project=project)
    item = StoreItem.objects.get(item_description="Copper Pipe", size="1/2 inch")
    txn = StoreTransaction.objects.first()
    amc = AMCContract.objects.get(customer=customer)
    return {
        "customer": customer,
        "service": service,
        "project": project,
        "boq": boq,
        "issue": issue,
        "item": item,
        "txn": txn,
        "amc": amc,
    }


def scene_sets(records):
    main = [
        ("Complete business overview", "/dashboard/", 6.0, "scroll"),
        ("Manage all customers in one place", "/customers/", 5.5, "none"),
        ("Open full customer details", f"/customers/detail/{records['customer'].id}/", 5.5, "scroll"),
        ("Maintain complete service history", "/complaints/customer-history/", 5.5, "scroll"),
        ("Track service schedules", "/customers/service-schedules/", 5.5, "scroll"),
        ("Monitor repair job status", "/service/", 5.5, "none"),
        ("Review a service request", f"/service/detail/{records['service'].id}/", 5.5, "scroll"),
        ("Manage installation projects", "/projects/", 5.5, "none"),
        ("Open commercial project details", f"/projects/detail/{records['project'].id}/", 6.0, "scroll"),
        ("Prepare BOQs and quotations", f"/boq/detail/{records['boq'].id}/", 6.0, "scroll"),
        ("Track AMC contracts", "/amc/", 5.5, "none"),
        ("Review AMC visit planning", f"/amc/detail/{records['amc'].id}/", 5.5, "scroll"),
        ("Monitor inventory and spare parts", "/store/items/", 5.5, "none"),
        ("View stock movement records", "/store/transactions/", 5.5, "none"),
        ("Record material issued to teams", f"/material-issue/detail/{records['issue'].id}/", 6.0, "scroll"),
        ("Review reports and business control", "/reports/", 5.5, "none"),
    ]
    short = [
        ("Complete business overview", "/dashboard/", 4.5, "none"),
        ("Customers and service history", f"/customers/detail/{records['customer'].id}/", 4.5, "scroll"),
        ("Track service and job status", "/service/", 4.5, "none"),
        ("Projects, BOQs and quotations", f"/boq/detail/{records['boq'].id}/", 4.5, "scroll"),
        ("AMC visits and follow-ups", f"/amc/detail/{records['amc'].id}/", 4.5, "scroll"),
        ("Inventory and spare parts", "/store/items/", 4.5, "none"),
        ("Material issue and reports", f"/material-issue/detail/{records['issue'].id}/", 4.5, "scroll"),
    ]
    return main, short


def write_srt(scenes, path):
    def fmt(seconds):
        ms = int(round((seconds - int(seconds)) * 1000))
        s = int(seconds) % 60
        m = int(seconds // 60) % 60
        h = int(seconds // 3600)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    t = 0.0
    parts = []
    for idx, (caption, _route, dur, _action) in enumerate(scenes, 1):
        start = t + 0.25
        end = min(t + dur - 0.25, start + max(2.8, dur - 0.7))
        parts.append(f"{idx}\n{fmt(start)} --> {fmt(end)}\n{caption}\n")
        t += dur
    path.write_text("\n".join(parts))


def draw_centered(draw, text, font, y, fill, max_width):
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (W - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += (bbox[3] - bbox[1]) + 18
    return y


def make_card(kind, out):
    img = Image.new("RGB", (W, H), "#f8fbff")
    draw = ImageDraw.Draw(img)
    # subtle diagonal bands
    for i in range(-W, W, 90):
        draw.polygon([(i, H), (i+260, H), (i+W+260, 0), (i+W, 0)], fill="#eef8ff")
    draw.rounded_rectangle((170, 160, W-170, H-160), radius=42, fill="white", outline="#d8ecf8", width=2)
    title_font = ImageFont.truetype(FONT_BOLD, 74)
    sub_font = ImageFont.truetype(FONT_REG, 38)
    small_font = ImageFont.truetype(FONT_BOLD, 34)
    if kind == "title":
        draw.text((W/2, 310), "Air Conditioning Services ERP", font=title_font, fill="#0F4C81", anchor="mm")
        draw.text((W/2, 400), "Customers, service, projects, AMC and inventory", font=sub_font, fill="#27364a", anchor="mm")
        draw.text((W/2, 455), "in one organized system", font=sub_font, fill="#27364a", anchor="mm")
        draw.rounded_rectangle((720, 575, 1200, 655), radius=18, fill="#0F4C81")
        draw.text((W/2, 615), "Professional Software Demo", font=small_font, fill="white", anchor="mm")
    else:
        draw_centered(draw, "Manage your complete air-conditioning service business from one organized system.", title_font, 285, "#0F4C81", W-520)
        draw.text((W/2, 555), "Customizable for your business", font=sub_font, fill="#27364a", anchor="mm")
        draw.rounded_rectangle((735, 660, 1185, 740), radius=18, fill="#0F4C81")
        draw.text((W/2, 700), "Request a Personalized Demo", font=small_font, fill="white", anchor="mm")
    img.save(out)


def make_thumbnail(out, subtitle):
    img = Image.new("RGB", (W, H), "#0F4C81")
    draw = ImageDraw.Draw(img)
    for r, color in [(880, "#155d99"), (640, "#22b8cf"), (430, "#ffffff")]:
        draw.ellipse((W-r//2, -r//3, W+r//2, r), fill=color)
    draw.rectangle((0, 0, W, H), fill=(15, 76, 129))
    title_font = ImageFont.truetype(FONT_BOLD, 84)
    sub_font = ImageFont.truetype(FONT_REG, 42)
    draw.text((130, 330), "AC Service ERP", font=title_font, fill="white")
    draw.text((132, 440), subtitle, font=sub_font, fill="#dff7ff")
    draw.rounded_rectangle((130, 585, 770, 680), radius=22, fill="white")
    draw.text((165, 608), "Customers • AMC • Stock • Reports", font=ImageFont.truetype(FONT_BOLD, 34), fill="#0F4C81")
    img.save(out)


def login_and_save_state(playwright, state_path):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
    page = context.new_page()
    page.goto(BASE_URL + "/login/", wait_until="networkidle")
    page.fill('input[name="username"]', 'demo_ceo')
    page.fill('input[name="password"]', 'Demo@12345')
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard/**", timeout=15000)
    context.storage_state(path=str(state_path))
    browser.close()


def capture_flow(playwright, scenes, raw_name, state_path):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": W, "height": H},
        device_scale_factor=1,
        storage_state=str(state_path),
        record_video_dir=str(RAW),
        record_video_size={"width": W, "height": H},
    )
    page = context.new_page()
    page.set_default_timeout(20000)
    for caption, route, dur, action in scenes:
        page.goto(BASE_URL + route, wait_until="networkidle")
        page.evaluate("""(caption) => {
            document.body.style.cursor='default';
            const old = document.getElementById('video-caption-overlay');
            if (old) old.remove();
            const el = document.createElement('div');
            el.id = 'video-caption-overlay';
            el.textContent = caption;
            el.style.position = 'fixed';
            el.style.left = '50%';
            el.style.bottom = '44px';
            el.style.transform = 'translateX(-50%)';
            el.style.zIndex = '999999';
            el.style.background = 'rgba(10, 20, 35, 0.82)';
            el.style.color = 'white';
            el.style.fontFamily = 'Arial, sans-serif';
            el.style.fontSize = '36px';
            el.style.fontWeight = '700';
            el.style.lineHeight = '1.25';
            el.style.padding = '18px 30px';
            el.style.borderRadius = '18px';
            el.style.boxShadow = '0 16px 45px rgba(15, 23, 42, 0.28)';
            el.style.maxWidth = '82vw';
            el.style.textAlign = 'center';
            el.style.pointerEvents = 'none';
            document.body.appendChild(el);
        }""", caption)
        page.mouse.move(1500, 220, steps=20)
        time.sleep(0.8)
        if action == "scroll":
            page.mouse.wheel(0, 480)
            time.sleep(max(1.2, dur - 2.6))
            page.mouse.wheel(0, -260)
            time.sleep(0.6)
        else:
            time.sleep(dur - 0.8)
    video = page.video
    page.close()
    video.save_as(str(RAW / raw_name))
    context.close()
    browser.close()


def ffmpeg_make_clip(image, duration, out):
    run(["ffmpeg", "-y", "-loop", "1", "-t", str(duration), "-i", str(image), "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)])


def burn_captions(raw, srt, out):
    vf = f"fps={FPS},scale={W}:{H},format=yuv420p"
    run(["ffmpeg", "-y", "-i", str(raw), "-vf", vf, "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", str(out)])


def concat(parts, out):
    list_path = RAW / (out.stem + "-concat.txt")
    list_path.write_text("\n".join(f"file '{p.resolve()}'" for p in parts))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(out)])


def produce_one(name, scenes, title_card, closing_card, final_out):
    state = RAW / "storage-state.json"
    raw = RAW / f"{name}-browser.webm"
    srt = RAW / f"{name}-captions.srt"
    captioned = RAW / f"{name}-captioned.mp4"
    title_clip = RAW / f"{name}-title.mp4"
    closing_clip = RAW / f"{name}-closing.mp4"
    write_srt(scenes, srt)
    with sync_playwright() as p:
        login_and_save_state(p, state)
        capture_flow(p, scenes, raw.name, state)
    ffmpeg_make_clip(title_card, OPENING, title_clip)
    ffmpeg_make_clip(closing_card, CLOSING if name == "main" else 4.0, closing_clip)
    burn_captions(raw, srt, captioned)
    concat([title_clip, captioned, closing_clip], final_out)
    return raw, srt


def write_docs(main_scenes, short_scenes, records):
    (VP / "verified-routes.md").write_text("# Verified Routes\n\n" + "\n".join(f"- `{route}` - {caption}" for caption, route, *_ in main_scenes))
    (VP / "caption-timeline.md").write_text("# Caption Timeline\n\n## Main Video\n" + "\n".join(f"- {caption}" for caption, *_ in main_scenes) + "\n\n## WhatsApp Video\n" + "\n".join(f"- {caption}" for caption, *_ in short_scenes))
    (VP / "client-demo-flow.md").write_text("# Client Demo Flow\n\n" + "\n".join(f"{i}. {caption} - `{route}`" for i,(caption,route,*_) in enumerate(main_scenes,1)))
    shown = f"""# Records Shown\n\n- Customer: {records['customer'].customer_name}\n- Service request: {records['service'].complaint_id} - {records['service'].nature_of_complaint}\n- Project: {records['project'].project_id} - {records['project'].site_name}\n- BOQ: {records['boq'].boq_id} - {records['boq'].title}\n- AMC contract: {records['amc'].amc_id} - {records['customer'].customer_name}\n- Material issue: {records['issue'].issue_id} - {records['issue'].heading}\n- Inventory item: {records['item'].item_code} - {records['item'].item_description} {records['item'].size}\n- Store transaction: {records['txn'].transaction_id}\n"""
    (VP / "recording-notes.md").write_text("# Recording Notes\n\nNo voice-over was used. No browser chrome, credentials, terminal, code, or localhost URL is visible in the browser capture.\n\n" + shown)
    (VP / "README.md").write_text("# Video Production\n\nRun from the project root:\n\n```bash\nsource venv/bin/activate\npython marketing-assets/video-production/production-script/produce_videos.py\n```\n\nOutputs are written to `marketing-assets/video-production/exports/`.\n")


def main():
    reset_data()
    records = get_records()
    main_scenes, short_scenes = scene_sets(records)
    write_docs(main_scenes, short_scenes, records)
    title = CARDS / "opening-title.png"
    closing = CARDS / "closing-card.png"
    make_card("title", title)
    make_card("closing", closing)
    make_thumbnail(THUMBS / "main-video-thumbnail.png", "Complete Business Control")
    make_thumbnail(THUMBS / "whatsapp-preview-thumbnail.png", "Quick Software Demo")
    proc = start_server()
    try:
        produce_one("main", main_scenes, title, closing, EXPORTS / "ac-erp-client-demo.mp4")
        produce_one("whatsapp", short_scenes, title, closing, EXPORTS / "ac-erp-whatsapp-demo.mp4")
    finally:
        stop_server(proc)


if __name__ == "__main__":
    main()
