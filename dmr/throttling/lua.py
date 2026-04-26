from typing import Final

# Simple rate
# -----------

SIMPLE_RATE: Final = """
-- simple_rate.lua
-- Fixed-window rate limiter for Redis
--
-- KEYS[1]  : cache key (e.g. "throttle:<user>:<endpoint>")
-- ARGV[1]  : max_requests   (integer)
-- ARGV[2]  : window_seconds (integer TTL for the fixed window)
-- ARGV[3]  : view_only      (integer whether or not we only want to view data)
--
-- Returns a three-element array:
--   [1]  allowed    : 1 = request allowed, 0 = denied
--   [2]  current    : request count AFTER this call (or at time of denial)
--   [3]  ttl        : seconds remaining in the current window

local key          = KEYS[1]
local max_requests = tonumber(ARGV[1])
local window       = tonumber(ARGV[2])
local view_only    = tonumber(ARGV[3])

-- Current counter:
local current = 0

if view_only == 0 then
    -- Atomically increment the counter.
    -- If the key didn't exist, Redis creates it starting at 1.
    current = redis.call("INCR", key)

    -- On the very first request in a window, stamp the TTL.
    if current == 1 then
        redis.call("EXPIRE", key, window)
    end
else
    -- When reading the key, we don't have to do anything special.
    current = tonumber(redis.call("GET", key))
end

local ttl = redis.call("TTL", key)
-- Use Redis server clock so the timestamp is always consistent
-- with the data stored in Redis (no Python <-> Redis skew).
local time_reply = redis.call("TIME")        -- {seconds, microseconds}
local now        = tonumber(time_reply[1])   -- integer seconds
local expire_at  = now + ttl

if current > max_requests then
    if view_only == 0 then
        -- Undo the increment so the counter stays at the cap,
        -- making the "current" value honest for the caller.
        redis.call("DECR", key)
    end
    return {0, max_requests, expire_at}
end

return {1, current, expire_at}
"""

# Leaky bucket
# ------------

LEAKY_BUCKET: Final = """
-- leaky_bucket.lua
--
-- KEYS[1]  : cache key  (e.g. "throttle:<user>:<endpoint>")
-- ARGV[1]  : max_requests        (integer)
-- ARGV[2]  : duration_in_seconds (integer)
-- ARGV[3]  : view_only      (integer whether or not we only want to view data)
--
-- Scaled-unit invariant (mirrors the Python class):
--   capacity  = max_requests * duration_in_seconds
--   per-request cost  = +duration_in_seconds
--   leak rate         = max_requests scaled-units / second
--
-- Returns a three-element array:
--   [1] allowed      : 1 = request allowed, 0 = denied
--   [2] level        : current scaled level AFTER this call
--   [3] capacity     : max_requests * duration_in_seconds

local key          = KEYS[1]
local max_requests = tonumber(ARGV[1])
local duration     = tonumber(ARGV[2])
local view_only    = tonumber(ARGV[3])
local capacity     = max_requests * duration

-- Use Redis server clock so the timestamp is always consistent
-- with the data stored in Redis (no Python <-> Redis skew).
local time_reply = redis.call("TIME")        -- {seconds, microseconds}
local now        = tonumber(time_reply[1])   -- integer seconds

-- ── load stored state ──────────────────────────────────────────────────────
local raw       = redis.call("HMGET", key, "level", "last_time")
local level     = tonumber(raw[1]) or 0
local last_time = tonumber(raw[2]) or now

-- ── leak ───────────────────────────────────────────────────────────────────
-- Every elapsed second drains max_requests scaled units.
local elapsed = math.max(0, now - last_time)
level         = math.max(0, level - elapsed * max_requests)

-- ── check capacity (mirrors `>= max_requests * duration_in_seconds`) ───────
if level >= capacity then
    -- Do NOT update stored state — the bucket is full, nothing changes.
    return {0, level, capacity}
end

-- Only update values, when non-viewing:
if view_only == 0 then
    -- ── fill (+duration_in_seconds scaled units) ───────────────────────────
    level = level + duration

    -- Persist level and the current timestamp.
    redis.call("HSET", key, "level", level, "last_time", now)
    -- TTL: after 2x the window of total inactivity
    -- the key expires automatically.
    redis.call("EXPIRE", key, duration * 2)
end

return {1, level, capacity}
"""
