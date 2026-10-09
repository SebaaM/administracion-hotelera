from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from django.test import TransactionTestCase
from django.db import close_old_connections, connections
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from pms.models import Room,Unit,Reservation
from imports.models import ImportProfile,ImportDraft,ImportBatch
from imports.services import save_decisions
from imports.apply import apply_draft
from .fixtures import source_candidate

class ImportConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user=User.objects.create_user("administrador",is_staff=True)
        room=Room.objects.create(name="2",kind="SHARED")
        self.unit=Unit.objects.create(room=room,name="a")
        self.profile=ImportProfile.objects.create(name="Perfil",configuration={"mapping":{"2-a":self.unit.pk},"mapping_confirmed":True})
    def prepare(self):
        today=timezone.localdate()
        c=source_candidate(start=(today+timedelta(days=1)).isoformat(),end=(today+timedelta(days=4)).isoformat())
        draft=ImportDraft.objects.create(profile=self.profile,user=self.user,fingerprint="a"*64,source={"format":"csv","sheets":[],"candidates":[c]},configuration=self.profile.configuration)
        save_decisions(draft.pk,1,{"rows":{c["key"]:{"reviewed":True,"new_confirmed":True,"status":"CONFIRMED"}}},self.user)
        draft.refresh_from_db();return draft
    def concurrent(self,drafts):
        barrier=Barrier(2);user_id=self.user.pk
        def work(draft):
            close_old_connections()
            try:
                user=User.objects.get(pk=user_id);barrier.wait(timeout=10)
                return ("ok",apply_draft(draft.pk,draft.revision,user).pk)
            except ValidationError:return ("conflict",None)
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(work,drafts))
    def test_two_drafts_cannot_claim_same_bed(self):
        result=self.concurrent([self.prepare(),self.prepare()])
        self.assertEqual(sorted(r[0] for r in result),["conflict","ok"])
        self.assertEqual(Reservation.objects.count(),1)
        self.assertEqual(ImportBatch.objects.count(),1)
    def test_same_draft_has_one_batch_under_double_confirmation(self):
        draft=self.prepare();result=self.concurrent([draft,draft])
        self.assertEqual([r[0] for r in result],["ok","ok"])
        self.assertEqual(result[0][1],result[1][1])
        self.assertEqual(ImportBatch.objects.count(),1)
