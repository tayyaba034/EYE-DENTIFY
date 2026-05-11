require('dotenv').config();
const { Client } = require('pg');
const { createClient } = require('@supabase/supabase-js');

const LOCAL_DB = {
  host: 'localhost',
  port: 5432,
  user: 'postgres',
  password: 'qwertyqwerty',
  database: 'postgres',
};

const TABLES = [
  { name: 'users', pk: 'user_id' },
  { name: 'missing_persons', pk: 'missing_person_id' },
  { name: 'media', pk: 'media_id' },
  { name: 'detections', pk: 'detection_id' },
  { name: 'alerts', pk: 'alert_id' },
  { name: 'system_logs', pk: 'log_id' },
  { name: 'cameras', pk: 'camera_id' },
  { name: 'device_tokens', pk: 'id' },
];

async function tableExistsInSupabase(supabase, tableName) {
  const { error } = await supabase.from(tableName).select('*').limit(1);
  return !error;
}

async function copyTable(localClient, supabase, tableName, pk) {
  const { rows } = await localClient.query(`select * from public.${tableName}`);
  if (!rows.length) {
    console.log(`[${tableName}] local empty, skipping`);
    return;
  }

  const batchSize = 250;
  let copied = 0;

  for (let i = 0; i < rows.length; i += batchSize) {
    const batch = rows.slice(i, i + batchSize);
    const query = supabase.from(tableName).upsert(batch, { onConflict: pk });
    const { error } = await query;
    if (error) {
      throw new Error(`[${tableName}] ${error.message}`);
    }
    copied += batch.length;
  }

  console.log(`[${tableName}] copied ${copied} rows`);
}

async function copyUsersToProfiles(localClient, supabase) {
  const { rows } = await localClient.query(`
    select user_id, email, full_name, role, created_at
    from public.users
  `);
  if (!rows.length) {
    console.log('[profiles] no users to map');
    return;
  }

  const profileRows = rows
    .filter((u) => u.user_id && String(u.user_id).length > 0)
    .map((u) => ({
      id: String(u.user_id),
      email: u.email,
      full_name: u.full_name || 'Unknown',
      role: u.role || 'user',
      created_at: u.created_at,
      updated_at: new Date().toISOString(),
    }));

  if (!profileRows.length) {
    console.log('[profiles] skipped (ids not compatible with UUID)');
    return;
  }

  const { error } = await supabase.from('profiles').upsert(profileRows, { onConflict: 'id' });
  if (error) {
    console.log(`[profiles] skipped: ${error.message}`);
    return;
  }
  console.log(`[profiles] copied ${profileRows.length} rows`);
}

async function main() {
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY');
  }

  const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const localClient = new Client(LOCAL_DB);
  await localClient.connect();

  try {
    for (const t of TABLES) {
      const hasTable = await tableExistsInSupabase(supabase, t.name);
      if (!hasTable) {
        console.log(`[${t.name}] missing in Supabase, skipping`);
        continue;
      }
      await copyTable(localClient, supabase, t.name, t.pk);
    }

    if (await tableExistsInSupabase(supabase, 'profiles')) {
      await copyUsersToProfiles(localClient, supabase);
    } else {
      console.log('[profiles] missing in Supabase, skipping');
    }
  } finally {
    await localClient.end();
  }
}

main()
  .then(() => {
    console.log('Copy finished');
    process.exit(0);
  })
  .catch((err) => {
    console.error('Copy failed:', err.message);
    process.exit(1);
  });

