-- Singular test: reco_interactions.customer_id must reference a valid pharmacy_id or hospital_id.
select interaction_id, customer_id
from {{ ref('bronze_reco_interactions') }}
where customer_id is not null
  and customer_id not in (select pharmacy_id from {{ ref('bronze_pharmacies') }})
  and customer_id not in (select hospital_id from {{ ref('bronze_hospitals') }})
