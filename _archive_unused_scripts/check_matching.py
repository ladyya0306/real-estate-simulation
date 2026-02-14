import sqlite3

db_path = r'd:\GitProj\oasis-main\results\run_20260209_205146\simulation.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('=== MATCHING DIAGNOSTICS ===\n')

# Check how many listings exist
cursor.execute('SELECT COUNT(*) FROM properties_market WHERE status="for_sale"')
listing_count = cursor.fetchone()[0]
print(f'Total Listings: {listing_count}')

# Check buyer details
cursor.execute('SELECT agent_id, target_zone, max_price FROM active_participants WHERE role IN ("BUYER", "BUYER_SELLER") LIMIT 10')
rows = cursor.fetchall()
print('\nSample Buyers (first 10):')
for r in rows:
    zone = r[1] if r[1] else 'NULL'
    print(f'  Agent {r[0]}: Zone={zone}, MaxPrice={r[2]:,.0f}')

# Check listing details and zones
cursor.execute('''
    SELECT pm.property_id, pm.listed_price, pm.min_price, ps.zone
    FROM properties_market pm
    JOIN properties_static ps ON pm.property_id = ps.property_id
    WHERE pm.status="for_sale"
    LIMIT 10
''')
rows = cursor.fetchall()
print('\nSample Listings (first 10):')
for r in rows:
    print(f'  Property {r[0]}: Zone={r[3]}, Listed={r[1]:,.0f}, Min={r[2]:,.0f}')

# Zone distribution
cursor.execute('''
    SELECT ps.zone, COUNT(*)
    FROM properties_market pm
    JOIN properties_static ps ON pm.property_id = ps.property_id
    WHERE pm.status="for_sale"
    GROUP BY ps.zone
''')
rows = cursor.fetchall()
print('\nListings by Zone:')
for r in rows:
    print(f'  Zone {r[0]}: {r[1]} listings')

# Buyer target zones
cursor.execute('''
    SELECT target_zone, COUNT(*)
    FROM active_participants
    WHERE role IN ("BUYER", "BUYER_SELLER")
    GROUP BY target_zone
''')
rows = cursor.fetchall()
print('\nBuyers by Target Zone:')
for r in rows:
    zone_str = r[0] if r[0] else 'NULL'
    print(f'  Zone {zone_str}: {r[1]} buyers')

# Price range analysis
cursor.execute('''
    SELECT MIN(pm.listed_price), MAX(pm.listed_price), AVG(pm.listed_price)
    FROM properties_market pm
    WHERE pm.status="for_sale"
''')
r = cursor.fetchone()
print('\nListing Price Range:')
print(f'  Min: {r[0]:,.0f}, Max: {r[1]:,.0f}, Avg: {r[2]:,.0f}')

cursor.execute('''
    SELECT MIN(max_price), MAX(max_price), AVG(max_price)
    FROM active_participants
    WHERE role IN ("BUYER", "BUYER_SELLER")
''')
r = cursor.fetchone()
print('\nBuyer Max Price Range:')
print(f'  Min: {r[0]:,.0f}, Max: {r[1]:,.0f}, Avg: {r[2]:,.0f}')

conn.close()
