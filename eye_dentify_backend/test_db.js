require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env");
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function testConnection() {
  console.log(`Testing connection to: ${supabaseUrl}`);
  try {
    const { data, error } = await supabase.from('alerts').select('*').limit(1);
    if (error) {
      console.error("Connection error:", error.message);
      if (error.message.includes("521")) {
        console.error("HTTP 521: The Supabase project might be paused or down.");
      }
    } else {
      console.log("Successfully connected to 'alerts' table!");
      console.log("Data sample:", data);
    }
  } catch (err) {
    console.error("Unexpected error:", err);
  }
}

testConnection();
