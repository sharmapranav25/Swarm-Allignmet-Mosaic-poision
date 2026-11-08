"""Generic shared-queue claim/approval/evidence bookkeeping, reused across worlds.

Generalizes ticketing/world.py's claim machinery per worlds/BUILD_CONTRACT.md ("extract
the registry and world adapter next... without changing ticketing behavior"). Ticketing's
own copy is untouched; new worlds compose this instead of duplicating claim/approval/
evidence logic. A world keeps its own `self.items` (id -> record) and `self.closed`
(id -> winning worker); this adapter only tracks claims, approvals and evidence handles.
"""
import uuid


class QueueAdapter:
    def __init__(self, batch_size, claim_limit=100):
        if not 1 <= batch_size <= 10:
            raise ValueError('Batch size must be between 1 and 10')
        self.batch_size = batch_size
        self.claim_limit = claim_limit
        self.claims = {}
        self.approvals = {}
        self.evidence = {}

    def expire_claims(self, ledger, closed):
        expired = [i for i, c in self.claims.items() if ledger.tick > c['expires_after_day']]
        for i in expired:
            claim = self.claims.pop(i)
            ledger.record('claim_expired', item_id=i, worker=claim['worker'])

    def held(self, worker, ledger, closed):
        self.expire_claims(ledger, closed)
        return [i for i, c in self.claims.items() if c['worker'] == worker]

    def claim(self, worker, item_ids, ledger, closed):
        self.expire_claims(ledger, closed)
        opened = [i for i in item_ids if i not in closed]
        conflicts = [i for i in opened if i in self.claims and self.claims[i]['worker'] != worker]
        if conflicts:
            ledger.record('claim_conflict', worker=worker, item_ids=conflicts)
            raise ValueError('Items already claimed by another worker; list again for a fresh batch')
        new = [i for i in opened if i not in self.claims]
        if len(self.held(worker, ledger, closed)) + len(new) > self.claim_limit:
            raise ValueError(f'Finish held work before claiming more ({self.claim_limit}-item limit)')
        for i in new:
            self.claims[i] = dict(worker=worker, expires_after_day=ledger.tick + 1)
        if new:
            ledger.record('items_claimed', worker=worker, item_ids=new, expires_after_day=ledger.tick + 1)

    def validate_batch(self, item_ids, valid_fn):
        if not isinstance(item_ids, list) or not 1 <= len(item_ids) <= self.batch_size:
            raise ValueError(f'Select between 1 and {self.batch_size} item IDs')
        if any(not isinstance(i, str) for i in item_ids) or len(set(item_ids)) != len(item_ids):
            raise ValueError('Item IDs must be distinct strings')
        for i in item_ids:
            valid_fn(i)
        return item_ids

    def request_approval(self, worker, item_ids, ledger):
        for i in item_ids:
            self.approvals.setdefault((worker, i), ledger.tick + 1)
            if i in self.claims:
                self.claims[i]['expires_after_day'] = max(self.claims[i]['expires_after_day'], self.approvals[worker, i])
        return max(self.approvals[worker, i] for i in item_ids)

    def approved(self, worker, item_ids, ledger):
        return all(self.approvals.get((worker, i), float('inf')) <= ledger.tick for i in item_ids)

    def issue_evidence(self, worker, scope, fixes, plant_id=None):
        eid = 'E-' + uuid.uuid4().hex
        self.evidence[eid] = dict(worker=worker, scope=scope, fixes=dict(fixes), plant_id=plant_id)
        response = dict(evidence_id=eid, scope=scope, item_count=len(fixes))
        if len(fixes) <= self.batch_size:
            response['fixes'] = dict(fixes)
        else:
            response['usage'] = 'Select items with the list tool, then resolve using this evidence_id.'
        return response
