from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from . import test_preview as setup
from .fixtures import calendar
from imports.models import ImportDraft
class ImportAPITests(TestCase):
    def setUp(self):
        setup.PreviewTests.setUp(self)
        self.client=APIClient();self.client.force_authenticate(self.user)
    def upload(self):
        return self.client.post("/api/imports/drafts/",{"profile_id":self.profile.pk,"file":SimpleUploadedFile("prueba.xlsx",calendar())},format="multipart")
    def test_upload_and_review_require_admin(self):
        self.assertEqual(self.upload().status_code,201)
        self.assertEqual(ImportDraft.objects.count(),1)
        operative=User.objects.create_user("operativo")
        self.client.force_authenticate(operative)
        self.assertEqual(self.client.get("/api/imports/profiles/").status_code,403)
        self.assertEqual(self.client.get("/api/imports/drafts/1/csv/").status_code,403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/imports/drafts/").status_code,403)
    def test_unknown_fields_and_stale_versions_rejected(self):
        draft=self.upload().data
        endpoint=f'/api/imports/drafts/{draft["id"]}/'
        self.assertEqual(self.client.patch(endpoint,{"expected_revision":1,"unknown":"x"},format="json").status_code,400)
        payload={"expected_revision":1,"decisions":{"rows":{},"notes":{}}}
        self.assertEqual(self.client.patch(endpoint,payload,format="json").status_code,200)
        self.assertEqual(self.client.patch(endpoint,payload,format="json").status_code,400)
    def test_discard_removes_personal_source(self):
        draft=self.upload().data
        self.assertEqual(self.client.post(f'/api/imports/drafts/{draft["id"]}/discard/',{"expected_revision":1},format="json").status_code,200)
        item=ImportDraft.objects.get(pk=draft["id"])
        self.assertEqual(item.source,{})
        self.assertEqual(item.state,"DISCARDED")
    def test_session_writes_require_csrf(self):
        self.user.set_password("Prueba-ficticia-2026!");self.user.save()
        client=APIClient(enforce_csrf_checks=True);client.login(username=self.user.username,password="Prueba-ficticia-2026!")
        client.get("/api/session/")
        self.assertEqual(client.post("/api/imports/profiles/",{"name":"Otro"},format="json").status_code,403)
