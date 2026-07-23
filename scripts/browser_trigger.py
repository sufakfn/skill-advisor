#!/usr/bin/env python3
"""
GitHub Workflow 浏览器触发器

用 Playwright 自动化操作 GitHub 网页，触发 workflow。

用法:
  python scripts/browser_trigger.py                      # 触发 sync workflow
  python scripts/browser_trigger.py --workflow ci.yml    # 触发指定 workflow
  python scripts/browser_trigger.py --full-rebuild       # 强制全量重建

前提:
  - 已安装 playwright: pip install playwright && python -m playwright install chromium
  - GitHub 已登录（首次运行会提示登录）
"""

import argparse
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

GITHUB_USER = os.environ.get("GITHUB_USER", "sufakfn")  # 从环境变量读取
REPO = os.environ.get("GITHUB_REPO", "skill-advisor")   # 从环境变量读取
PROFILE_DIR = Path.home() / ".skill-advisor-browser-profile"


def trigger_workflow(workflow_file="sync_skills.yml", full_rebuild=False, headless=False):
    """通过浏览器触发 GitHub workflow"""

    with sync_playwright() as p:
        # 使用持久化 context 保持登录状态
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )

        page = context.pages[0] if context.pages else context.new_page()

        # 1. 打开 workflow 页面
        url = f"https://github.com/{GITHUB_USER}/{REPO}/actions/workflows/{workflow_file}"
        print(f"[*] 打开: {url}")
        page.goto(url, wait_until="networkidle", timeout=30000)

        # 2. 检查是否需要登录
        if "login" in page.url.lower():
            print("[!] 需要登录 GitHub")
            print("[!] 请在浏览器窗口中登录（非 headless 模式）")
            page.wait_for_url(f"**/{GITHUB_USER}/{REPO}/**", timeout=120000)
            print("[*] 登录成功")

        # 3. 等待页面加载
        page.wait_for_timeout(2000)

        # 4. 先检查是否有 "Complete setup" 按钮（首次需要）
        complete_btn = page.locator("button:has-text('Complete setup'), button:has-text('完成设置')")
        if complete_btn.count() > 0:
            print("[*] 发现 Complete setup 按钮，点击...")
            complete_btn.first.click()
            page.wait_for_timeout(2000)

        # 5. 查找并点击 "Run workflow" 按钮
        print("[*] 查找 Run workflow 按钮...")

        # 尝试多种选择器
        run_btn = page.locator(
            "button:has-text('Run workflow'), "
            "summary:has-text('Run workflow'), "
            "[aria-label='Run workflow'], "
            ".btn-primary:has-text('Run')"
        )

        if run_btn.count() == 0:
            print("[!] 未找到 Run workflow 按钮")
            print("[*] 尝试备选方案...")
            # 备选：通过 URL API 触发
            print("[*] 尝试通过 GitHub API 触发...")
            import urllib.request
            api_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO}/actions/workflows/sync_skills.yml/dispatches"
            req = urllib.request.Request(api_url, method="POST",
                headers={"Accept": "application/vnd.github+json"},
                data=b'{"ref":"main"}')
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print(f"[+] API 触发成功: {resp.status}")
                    context.close()
                    return True
            except Exception as e:
                print(f"[!] API 触发也失败: {e}")

            print("[*] 截图保存到 debug_screenshot.png")
            page.screenshot(path="debug_screenshot.png")
            context.close()
            return False

        print(f"[*] 找到 {run_btn.count()} 个按钮，点击第一个")
        run_btn.first.click()
        page.wait_for_timeout(1000)

        # 5. 如果 full_rebuild，选择下拉选项
        if full_rebuild:
            print("[*] 选择强制全量重建...")
            # 点击下拉菜单（如果有）
            dropdown = page.locator("input[name='full_rebuild']")
            if dropdown.count() > 0:
                dropdown.first.check()

        # 6. 点击绿色的 "Run workflow"（确认）
        confirm_btn = page.locator("button:has-text('Run workflow')").last
        print("[*] 确认触发...")
        confirm_btn.click()

        # 7. 等待确认（页面应该跳转或显示成功）
        page.wait_for_timeout(3000)

        # 8. 验证结果
        # 向上箭头和分支之间的冲突
        if "actions/runs" in page.url:
            print("[+] 触发成功！页面已跳转到运行详情")
            run_id = page.url.split("/runs/")[-1].split("/")[0]
            print(f"[+] Run ID: {run_id}")
            success = True
        else:
            # 检查页面上的成功指示
            page_content = page.content()
            if "workflow" in page_content.lower():
                print("[+] 可能已触发，请检查 Actions 页面")
                success = True
            else:
                print("[?] 状态未知，请手动确认")
                print(f"[*] 当前 URL: {page.url}")
                success = None

        # 保存截图
        page.screenshot(path="trigger_result.png")
        print("[*] 截图保存到 trigger_result.png")

        context.close()
        return success


def main():
    """浏览器触发器主入口 — 通过 Playwright 自动化操作 GitHub 网页触发 workflow"""
    parser = argparse.ArgumentParser(description="GitHub Workflow 浏览器触发器")
    parser.add_argument("--workflow", default="sync_skills.yml", help="workflow 文件名")
    parser.add_argument("--full-rebuild", action="store_true", help="强制全量重建")
    parser.add_argument("--headless", action="store_true", help="无头模式（不可见浏览器）")
    parser.add_argument("--visible", action="store_true", default=True, help="可见浏览器（可登录）")
    args = parser.parse_args()

    headless = args.headless and not args.visible

    print("=" * 50)
    print("GitHub Workflow 浏览器触发器")
    print("=" * 50)
    print(f"  仓库: {args.workflow}")
    print(f"  全量重建: {args.full_rebuild}")
    print(f"  无头模式: {headless}")
    print()

    result = trigger_workflow(
        workflow_file=args.workflow,
        full_rebuild=args.full_rebuild,
        headless=headless
    )

    if result is True:
        print("\n[SUCCESS] 触发成功！")
    elif result is False:
        print("\n[FAILED] 触发失败")
    else:
        print("\n[UNKNOWN] 请手动确认")


if __name__ == "__main__":
    main()
