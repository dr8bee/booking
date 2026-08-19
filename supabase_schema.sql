-- 在 Supabase 專案的 SQL Editor 貼上並執行這段，建立報名紀錄資料表。

create table if not exists registrations (
    id bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    name text not null,
    phone text not null,
    email text,
    note text,
    amount integer not null,
    order_id text not null unique,
    status text not null default 'pending',   -- pending / paid / cancelled / confirm_failed
    transaction_id text
);

-- 依訂單編號查詢的效能索引（Streamlit 端每次確認付款、更新狀態都會用 order_id 查）
create index if not exists idx_registrations_order_id on registrations (order_id);

-- 這個系統的讀寫都是從 Streamlit 伺服器端用 service_role key 執行，
-- service_role key 本身就會繞過 RLS，所以不強制要求開 RLS。
-- 如果你想要更保守一點（例如以後有其他前端用 anon key 直接連 Supabase），
-- 可以另外開啟 RLS 並只允許 service_role 存取：
--
-- alter table registrations enable row level security;
