import os
os.environ['ENVIRONMENT']='DEPLOYED'
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('DROP TYPE IF EXISTS orderside CASCADE;'))
    conn.execute(text('DROP TYPE IF EXISTS orderstatus CASCADE;'))
    conn.commit()
print("Successfully dropped leftover types")
