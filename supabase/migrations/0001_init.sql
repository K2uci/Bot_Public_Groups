-- Esquema inicial del panel del Bot Facebook.
-- La web usa la clave publica de Supabase: TODOS los permisos los impone RLS (solo administradores).
-- El bot del VPS usa la service key (salta RLS) y es el unico que descifra las cookies.

-- ---------------------------------------------------------------- administradores
create table public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  creado timestamptz not null default now()
);

create or replace function public.es_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;

-- ---------------------------------------------------------------- clientes
create table public.clientes (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9_-]{2,40}$'),
  nombre text not null,
  activo boolean not null default false,
  hora_inicio text not null default '10:00' check (hora_inicio ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'),
  -- el intervalo entre publicaciones lo decide cada cliente: sin valor por defecto
  espera_min numeric not null check (espera_min >= 1),
  espera_max numeric not null,
  dias_semana int[] check (dias_semana is null or dias_semana <@ array[0,1,2,3,4,5,6]),
  max_grupos_dia int check (max_grupos_dia is null or max_grupos_dia > 0),
  tg_chat_id text,
  -- sobre cifrado {v,k,iv,ct}: solo la clave privada del VPS puede abrirlo
  cookies_cifradas jsonb,
  cookies_actualizadas timestamptz,
  creado timestamptz not null default now(),
  constraint espera_orden check (espera_min <= espera_max)
);

-- ---------------------------------------------------------------- grupos
create table public.grupos (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references public.clientes(id) on delete cascade,
  url text not null,
  nombre text,
  activo boolean not null default true,
  detectado timestamptz not null default now(),
  unique (cliente_id, url)
);

-- ---------------------------------------------------------------- publicaciones (texto + imagen)
create table public.publicaciones (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references public.clientes(id) on delete cascade,
  texto text not null,
  imagen_path text not null,
  activo boolean not null default true,
  orden int not null default 0,
  creada timestamptz not null default now(),
  actualizada timestamptz not null default now()
);

-- ---------------------------------------------------------------- historial
create table public.publicaciones_log (
  id bigint generated always as identity primary key,
  cliente_id uuid not null references public.clientes(id) on delete cascade,
  fecha date not null,
  grupo_url text not null,
  grupo_nombre text,
  publicacion_id uuid,
  ok boolean not null,
  motivo text,
  creado timestamptz not null default now()
);
create index on public.publicaciones_log (cliente_id, creado desc);

create table public.tandas_dia (
  cliente_id uuid not null references public.clientes(id) on delete cascade,
  fecha date not null,
  inicio text,
  fin text,
  publicados int not null default 0,
  fallidos int not null default 0,
  pendientes int not null default 0,
  total_grupos int not null default 0,
  nuevos_grupos int not null default 0,
  bloqueo text,
  abortada text,
  en_curso boolean not null default false,
  resumen_enviado boolean not null default false,
  actualizado timestamptz not null default now(),
  primary key (cliente_id, fecha)
);

-- ---------------------------------------------------------------- ordenes desde la web hacia el bot
create table public.ordenes (
  id bigint generated always as identity primary key,
  cliente_id uuid not null references public.clientes(id) on delete cascade,
  tipo text not null check (tipo in ('publicar_ahora','leer_grupos','enviar_resumen')),
  parametros jsonb not null default '{}'::jsonb,
  estado text not null default 'pendiente' check (estado in ('pendiente','en_proceso','hecha','error')),
  resultado text,
  creada timestamptz not null default now(),
  terminada timestamptz
);
create index on public.ordenes (estado, creada);

-- latido del bot (una sola fila)
create table public.bot_estado (
  id int primary key default 1 check (id = 1),
  ultima_conexion timestamptz not null default now(),
  version text,
  mensaje text
);

-- ---------------------------------------------------------------- RLS: solo administradores
alter table public.admins enable row level security;
alter table public.clientes enable row level security;
alter table public.grupos enable row level security;
alter table public.publicaciones enable row level security;
alter table public.publicaciones_log enable row level security;
alter table public.tandas_dia enable row level security;
alter table public.ordenes enable row level security;
alter table public.bot_estado enable row level security;

create policy "admin lee admins" on public.admins for select to authenticated using (public.es_admin());

create policy "admin todo" on public.clientes for all to authenticated using (public.es_admin()) with check (public.es_admin());
create policy "admin todo" on public.grupos for all to authenticated using (public.es_admin()) with check (public.es_admin());
create policy "admin todo" on public.publicaciones for all to authenticated using (public.es_admin()) with check (public.es_admin());
create policy "admin todo" on public.ordenes for all to authenticated using (public.es_admin()) with check (public.es_admin());
-- historial, tandas y latido: la web solo lee (escribe el bot con la service key)
create policy "admin lee" on public.publicaciones_log for select to authenticated using (public.es_admin());
create policy "admin lee" on public.tandas_dia for select to authenticated using (public.es_admin());
create policy "admin lee" on public.bot_estado for select to authenticated using (public.es_admin());

-- ---------------------------------------------------------------- imagenes (bucket privado)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('imagenes', 'imagenes', false, 8388608, array['image/jpeg','image/png','image/webp'])
on conflict (id) do nothing;

create policy "admin lee imagenes" on storage.objects for select to authenticated
  using (bucket_id = 'imagenes' and public.es_admin());
create policy "admin sube imagenes" on storage.objects for insert to authenticated
  with check (bucket_id = 'imagenes' and public.es_admin());
create policy "admin edita imagenes" on storage.objects for update to authenticated
  using (bucket_id = 'imagenes' and public.es_admin());
create policy "admin borra imagenes" on storage.objects for delete to authenticated
  using (bucket_id = 'imagenes' and public.es_admin());
