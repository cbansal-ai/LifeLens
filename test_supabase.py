from supabase_client import supabase

response = supabase.table("events").select("*").execute()

print("Response:")
print(response)

print("Data:")
print(response.data)