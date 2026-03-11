#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VyapaarClaw — Demo Reset Script
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Resets all state for a clean demo run.
# Usage: ./scripts/demo_reset.sh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

echo "🔄 Resetting VyapaarClaw demo state..."

# 1. Flush Redis (budgets, rate limits, idempotency)
echo "  ► Flushing Redis..."
docker exec vyapaarclaw-redis-1 redis-cli FLUSHALL 2>/dev/null || \
  redis-cli FLUSHALL 2>/dev/null || \
  echo "    ⚠ Redis not available (run: docker compose up -d redis)"

# 2. Reset PostgreSQL audit logs and re-seed policies
echo "  ► Resetting PostgreSQL..."
docker exec vyapaarclaw-postgres-1 psql -U vyapaar -d vyapaar_db -c "
  TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE;
" 2>/dev/null || echo "    ⚠ PostgreSQL not available"

# 3. Seed demo policies
echo "  ► Seeding demo policies..."
uv run python scripts/seed_policies.py 2>/dev/null || \
  echo "    ⚠ Seed script failed"

echo ""
echo "✅ Demo state reset complete."
echo "   Run: python demo/showcase_demo.py"
