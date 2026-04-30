from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_roles
from ..database import get_db
from ..django_bridge import init_django
from ..models import User

router = APIRouter(prefix="/admin/analytics", tags=["admin analytics"])


def _plan_distribution() -> dict[str, int]:
    from subscription.models import BillingHistory

    now = timezone.now()
    active_rows = (
        BillingHistory.objects.filter(end_date__gte=now)
        .select_related("plan")
        .order_by("user_id", "-start_date")
    )
    latest_by_user: dict[int, str] = {}
    for row in active_rows:
        if row.user_id not in latest_by_user:
            latest_by_user[row.user_id] = row.plan.name

    counts: dict[str, int] = {}
    for plan_name in latest_by_user.values():
        counts[plan_name] = counts.get(plan_name, 0) + 1
    return counts


@router.get("/summary", response_model=schemas.AdminAnalyticsSummaryResponse)
def analytics_summary(_: User = Depends(require_roles("Admin")), db: Session = Depends(get_db)):
    init_django()
    from subscription.models import APIUsage, BlogUser

    total_users = db.query(User).count()
    total_requests = APIUsage.objects.aggregate(total=Sum("total_requests"))["total"] or 0

    top_rows = (
        APIUsage.objects.values("user_id")
        .annotate(requests=Sum("total_requests"))
        .order_by("-requests")[:5]
    )
    user_ids = [row["user_id"] for row in top_rows]
    users_by_id = BlogUser.objects.in_bulk(user_ids)
    top_users = [
        schemas.TopUserAnalytics(
            user=(users_by_id[row["user_id"]].email if row["user_id"] in users_by_id else f"user-{row['user_id']}"),
            requests=int(row["requests"] or 0),
        )
        for row in top_rows
    ]

    return schemas.AdminAnalyticsSummaryResponse(
        total_users=int(total_users),
        total_requests=int(total_requests),
        top_users=top_users,
        plan_distribution=_plan_distribution(),
    )


@router.get("/usage-daily", response_model=schemas.AdminUsageDailyResponse)
def analytics_usage_daily(_: User = Depends(require_roles("Admin"))):
    init_django()
    from subscription.models import APIUsage

    today = timezone.localdate()
    start_date = today - timedelta(days=6)

    rows = (
        APIUsage.objects.filter(usage_date__gte=start_date, usage_date__lte=today)
        .values("usage_date")
        .annotate(requests=Sum("total_requests"))
        .order_by("usage_date")
    )
    by_date = {row["usage_date"]: int(row["requests"] or 0) for row in rows}

    daily_usage = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        daily_usage.append(schemas.UsageDailyItem(date=day.isoformat(), requests=by_date.get(day, 0)))

    return schemas.AdminUsageDailyResponse(daily_usage=daily_usage)


@router.get("/dashboard", response_class=HTMLResponse)
def analytics_dashboard():
    # Simple frontend dashboard (optional extension in task instructions).
    return HTMLResponse(
        """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Admin Analytics Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f6f8fb; color: #1f2937; }
    h1 { margin-bottom: 16px; }
    .row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
    .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; min-width: 180px; }
    .card h3 { margin: 0 0 8px 0; font-size: 14px; color: #4b5563; }
    .card .val { font-size: 24px; font-weight: 700; }
    .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
    input { padding: 8px; width: 100%; margin-bottom: 8px; border: 1px solid #d1d5db; border-radius: 6px; }
    button { padding: 10px 14px; border: 0; border-radius: 6px; background: #2563eb; color: white; cursor: pointer; }
    ol { margin: 8px 0 0 22px; }
  </style>
</head>
<body>
  <h1>Dashboard - Admin Analytics</h1>

  <div class="panel">
    <input id="token" placeholder="Paste Bearer token" />
    <input id="apiKey" placeholder="Paste X-API-Key" />
    <button onclick="loadData()">Load Analytics</button>
  </div>

  <div class="row">
    <div class="card"><h3>Total Users</h3><div class="val" id="totalUsers">-</div></div>
    <div class="card"><h3>Total Requests</h3><div class="val" id="totalRequests">-</div></div>
    <div class="card"><h3>Basic</h3><div class="val" id="planBasic">0</div></div>
    <div class="card"><h3>Pro</h3><div class="val" id="planPro">0</div></div>
    <div class="card"><h3>Enterprise</h3><div class="val" id="planEnterprise">0</div></div>
  </div>

  <div class="panel">
    <h3>API Requests (Last 7 Days)</h3>
    <canvas id="usageChart"></canvas>
  </div>

  <div class="panel">
    <h3>Top Users</h3>
    <ol id="topUsers"></ol>
  </div>

  <script>
    let chart;
    async function loadData() {
      const token = document.getElementById('token').value.trim();
      const apiKey = document.getElementById('apiKey').value.trim();
      const headers = { 'Authorization': `Bearer ${token}`, 'X-API-Key': apiKey };

      const [summaryRes, usageRes] = await Promise.all([
        fetch('/admin/analytics/summary', { headers }),
        fetch('/admin/analytics/usage-daily', { headers })
      ]);
      if (!summaryRes.ok || !usageRes.ok) {
        alert('Failed to load analytics. Check token/key and try again.');
        return;
      }
      const summary = await summaryRes.json();
      const usage = await usageRes.json();

      document.getElementById('totalUsers').textContent = summary.total_users;
      document.getElementById('totalRequests').textContent = summary.total_requests;
      document.getElementById('planBasic').textContent = summary.plan_distribution.Basic || 0;
      document.getElementById('planPro').textContent = summary.plan_distribution.Pro || 0;
      document.getElementById('planEnterprise').textContent = summary.plan_distribution.Enterprise || 0;

      const topEl = document.getElementById('topUsers');
      topEl.innerHTML = '';
      summary.top_users.forEach((u) => {
        const li = document.createElement('li');
        li.textContent = `${u.user} - ${u.requests}`;
        topEl.appendChild(li);
      });

      const labels = usage.daily_usage.map(x => x.date);
      const values = usage.daily_usage.map(x => x.requests);
      const ctx = document.getElementById('usageChart').getContext('2d');
      if (chart) chart.destroy();
      chart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [{ label: 'Requests', data: values }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
      });
    }
  </script>
</body>
</html>
        """
    )
