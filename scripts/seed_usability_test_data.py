"""Seed deterministic local data for browser usability regression tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.database import get_db_context
from app.models.article import Article
from app.models.collector_account import CollectorAccountType
from app.models.log import OperationLog
from app.models.monitored_account import MonitoredAccount, MonitoredAccountStatus
from app.models.proxy import Proxy, ServiceType
from app.models.user import UserRole
from app.services.auth_service import AuthService


VIEWER_EMAIL = "ui_regression_viewer@example.com"
VIEWER_PASSWORD = "password123"

ACCOUNTS = [
    {
        "biz": "just_we_machine_heart",
        "name": "机器之心",
        "fakeid": "MjM5ODI5Njc2MA==",
        "tier": 1,
        "score": 92,
        "intro": "关注人工智能研究、产业应用和大模型基础设施的中文科技媒体。",
        "avatar": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=240&h=240&fit=crop",
    },
    {
        "biz": "just_we_qbitai",
        "name": "量子位",
        "fakeid": "MzA3MzI4MjgzMw==",
        "tier": 1,
        "score": 89,
        "intro": "报道 AI、机器人、自动驾驶和前沿科技产品动态。",
        "avatar": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=240&h=240&fit=crop",
    },
    {
        "biz": "just_we_latepost",
        "name": "晚点 LatePost",
        "fakeid": "MzU0MDk3NzQ3Nw==",
        "tier": 2,
        "score": 82,
        "intro": "长期关注科技公司、商业组织和产业结构变化的深度报道。",
        "avatar": "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=240&h=240&fit=crop",
    },
    {
        "biz": "just_we_36kr",
        "name": "36氪",
        "fakeid": "MjM5OTQ2NDUxMA==",
        "tier": 2,
        "score": 76,
        "intro": "覆盖创业、投融资、新消费、企业服务与科技商业新闻。",
        "avatar": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=240&h=240&fit=crop",
    },
    {
        "biz": "just_we_infoq",
        "name": "InfoQ",
        "fakeid": "MzA3MzU4NTYyMw==",
        "tier": 3,
        "score": 68,
        "intro": "面向软件开发者和技术管理者的架构、工程实践与趋势内容。",
        "avatar": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=240&h=240&fit=crop",
    },
]

ARTICLES = [
    ("机器之心", "大模型 Agent 进入工程化阶段，评测体系开始重写", "agent", 0),
    ("机器之心", "多模态模型落地办公场景，数据闭环成为竞争关键", "multimodal", 1),
    ("量子位", "机器人公司密集发布通用操作模型，真实场景数据仍是瓶颈", "robotics", 2),
    ("量子位", "端侧 AI 开始进入手机和车机，推理成本被重新计算", "edge-ai", 3),
    ("晚点 LatePost", "AI 应用公司的组织结构变化：从增长团队转向工作流团队", "business", 4),
    ("36氪", "企业服务创业公司重估 AI 入口，垂直行业工具更受关注", "saas", 5),
    ("36氪", "内容平台的推荐系统升级，创作者开始关注可解释流量", "platform", 6),
    ("InfoQ", "从 RAG 到数据治理：企业知识库项目进入长期维护期", "rag", 7),
    ("InfoQ", "可观测性团队如何接入 AI 任务链路和失败分类", "observability", 8),
    ("晚点 LatePost", "自动化运营系统的边界：效率提升之后需要审计与风控", "automation", 9),
]


def source_url_for(account: dict) -> str:
    return f"https://weixin.sogou.com/weixin?type=1&query={account['name']}"


def article_url(slug: str) -> str:
    return f"https://mp.weixin.qq.com/s/just-we-demo-{slug}"


def article_body(title: str, account_name: str, topic: str) -> str:
    return (
        f"这是一篇基于公开议题整理的原创示例正文，用于 Just-We 本地演示，不复制原文内容。\n\n"
        f"{account_name} 关注的主题是“{title}”。从监测系统视角看，这类内容通常包含三个信号："
        "是否出现新的产品或模型能力、是否给出可验证的行业案例、是否暴露后续跟踪价值。\n\n"
        f"在 {topic} 场景里，系统会先记录标题、发布时间、封面图和正文摘要，再进入文字解析、"
        "图片解析和类型判断三段式流程。若命中目标类型，文章会进入聚合 Feed；若未命中，"
        "仍保留审计信息，方便后续调整关键词和 Tier 策略。\n\n"
        "这段示例正文特意包含多段文本，便于检查文章详情页的纯文本、富文本、图片资源和 AI JSON 展示。"
    )


async def upsert_monitored_account(db, owner_id, item: dict) -> MonitoredAccount:
    account = await db.scalar(
        select(MonitoredAccount).where(
            MonitoredAccount.owner_user_id == owner_id,
            MonitoredAccount.biz == item["biz"],
        )
    )
    payload = {
        "owner_user_id": owner_id,
        "biz": item["biz"],
        "fakeid": item["fakeid"],
        "name": item["name"],
        "source_url": source_url_for(item),
        "avatar_url": item["avatar"],
        "mp_intro": item["intro"],
        "current_tier": item["tier"],
        "composite_score": item["score"],
        "primary_fetch_mode": CollectorAccountType.MP_ADMIN,
        "fallback_fetch_mode": None,
        "status": MonitoredAccountStatus.MONITORING,
        "metadata_json": {
            "seeded_for": "usability_regression",
            "real_public_account_name": True,
            "source_note": "真实公众号名称，演示数据不复制真实正文。",
        },
        "strategy_config": {"sample_data": True},
    }
    if account is None:
        account = MonitoredAccount(**payload)
        db.add(account)
        await db.flush()
        return account
    for key, value in payload.items():
        setattr(account, key, value)
    return account


async def upsert_article(db, monitored: MonitoredAccount, title: str, topic: str, index: int) -> Article:
    url = article_url(topic)
    article = await db.scalar(select(Article).where(Article.url == url))
    published_at = datetime.now(timezone.utc) - timedelta(hours=6 * index + 2)
    cover = f"https://picsum.photos/seed/just-we-{topic}/900/520"
    images = [
        cover,
        f"https://picsum.photos/seed/just-we-{topic}-detail/900/420",
    ]
    content = article_body(title, monitored.name, topic)
    html = "".join(f"<p>{paragraph}</p>" for paragraph in content.split("\n\n"))
    payload = {
        "monitored_account_id": monitored.id,
        "title": title,
        "content": content,
        "content_html": html,
        "content_type": "demo_original_summary",
        "raw_content": html,
        "images": images,
        "original_images": images,
        "cover_image": cover,
        "url": url,
        "author": monitored.name,
        "published_at": published_at,
        "ai_relevance_ratio": round(0.66 + min(index, 6) * 0.04, 2),
        "ai_judgment": {"reason": "命中科技/AI 监测样例", "keywords": [topic, "AI", "行业观察"]},
        "ai_text_analysis": {
            "summary": f"{title} 的原创摘要样例。",
            "key_points": ["产品能力", "行业案例", "后续跟踪价值"],
            "topics": [topic, "AI"],
        },
        "ai_image_analysis": {
            "summary": "封面图用于演示图片资源展示。",
            "images": [{"url": cover, "role": "cover"}],
        },
        "ai_type_judgment": {
            "target_match": "是",
            "reason": "符合 AI/科技商业监测目标。",
            "confidence": 0.82,
            "matched_signals": [topic, "workflow"],
        },
        "ai_combined_analysis": {
            "reason": "文字和图片信号均可审计。",
            "keywords": [topic, "Just-We"],
        },
        "ai_target_match": "是",
        "ai_analysis_status": "success",
        "fetch_mode": "mp_admin",
        "source_payload": {
            "seeded_for": "usability_regression",
            "source_mode": "real_account_original_summary",
            "copyright_note": "正文为原创示例，不复制真实文章全文。",
        },
    }
    if article is None:
        article = Article(**payload)
        db.add(article)
        return article
    for key, value in payload.items():
        setattr(article, key, value)
    return article


async def main() -> None:
    async with get_db_context() as db:
        auth_service = AuthService(db)
        viewer = await auth_service.user_repo.get_by_email(VIEWER_EMAIL)
        if viewer is None:
            viewer = await auth_service.create_user(VIEWER_EMAIL, VIEWER_PASSWORD, UserRole.VIEWER.value)

        await db.execute(
            delete(Article).where(
                Article.url.in_(
                    [
                        "https://mp.weixin.qq.com/s/ui_regression_article",
                        "https://mp.weixin.qq.com/s/just-we-ui-detail-safety",
                        "https://mp.weixin.qq.com/s/ui-test-article-001",
                        "https://mp.weixin.qq.com/s/ui_detail_safety_test",
                    ]
                )
            )
        )
        await db.execute(
            delete(MonitoredAccount).where(
                MonitoredAccount.biz.in_(["ui_regression_biz", "test_ui_biz_001"]),
            )
        )

        account_map = {}
        for account_seed in ACCOUNTS:
            account = await upsert_monitored_account(db, viewer.id, account_seed)
            account_map[account.name] = account

        proxy = await db.scalar(
            select(Proxy).where(
                Proxy.host == "127.0.0.1",
                Proxy.port == 8899,
                Proxy.service_type == ServiceType.MP_LIST,
            )
        )
        if proxy is None:
            db.add(
                Proxy(
                    host="127.0.0.1",
                    port=8899,
                    service_type=ServiceType.MP_LIST,
                    success_rate=0,
                    is_active=True,
                )
            )

        for account_name, title, topic, index in ARTICLES:
            await upsert_article(db, account_map[account_name], title, topic, index)

        db.add(
            OperationLog(
                user_id=viewer.id,
                action="create_usability_seed",
                target_type="usability",
                target_id=0,
                detail="Seeded Just-We realistic article and public-account demo data",
            )
        )

        print(
            {
                "viewer": VIEWER_EMAIL,
                "viewer_password": VIEWER_PASSWORD,
                "monitored_accounts": len(ACCOUNTS),
                "articles": len(ARTICLES),
                "proxy": "127.0.0.1:8899",
            }
        )


if __name__ == "__main__":
    asyncio.run(main())
