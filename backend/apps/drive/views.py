import os
import tempfile
import zipfile

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.permissions.permissions import IsEmployee
from apps.pm.views import serve_document
from .access import can_delete, can_share, can_write, files_for, folders_for, readable_spaces
from .models import File, Folder, ShareLink, Space
from .serializers import FileSerializer, FolderSerializer, ShareLinkSerializer

MAX_ZIP_BYTES = 500 * 1024 * 1024
LINK_FILTERS = ['employee', 'project', 'transaction', 'expense', 'invoice', 'statement']


def with_counts(qs, user):
    c = user.clearance
    return qs.annotate(file_count=Count('files', filter=Q(files__classification__lte=c), distinct=True),
                       folder_count=Count('children', filter=Q(children__classification__lte=c), distinct=True))


def zip_response(files, root_name, base_folder=None):
    """Zip `files`, keeping their folder path below `base_folder`. Spooled to disk past 32 MB."""
    files = list(files.select_related('folder'))
    if sum(f.size for f in files) > MAX_ZIP_BYTES:
        raise ValidationError('This folder is larger than 500 MB. Download its subfolders separately.')
    base = len(base_folder.path()) if base_folder else 0
    tmp = tempfile.SpooledTemporaryFile(max_size=32 * 1024 * 1024)
    seen = set()
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            parts = (f.folder.path() if f.folder else [])[base:]
            arc = '/'.join([*parts, f.name])
            stem, ext = os.path.splitext(arc)
            n = 1
            while arc.lower() in seen:
                n += 1
                arc = f'{stem} ({n}){ext}'
            seen.add(arc.lower())
            try:
                with f.file.open('rb') as fh:
                    zf.writestr(arc, fh.read())
            except FileNotFoundError:
                continue
    tmp.seek(0)
    return FileResponse(tmp, as_attachment=True, filename=f'{root_name}.zip', content_type='application/zip')


@extend_schema(tags=['Drive'])
class SpacesView(APIView):
    """GET /api/drive/spaces/ -- the spaces this user can open, with sizes, plus how many files are linked to them."""
    permission_classes = [IsEmployee]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user = request.user
        out = []
        for space in readable_spaces(user):
            agg = files_for(user).filter(space=space).aggregate(n=Count('id'), size=Sum('size'))
            out.append({'id': space, 'label': Space(space).label, 'files': agg['n'], 'size': agg['size'] or 0,
                        'can_write': can_write(user, space), 'can_share': can_share(user, space)})
        return Response({'spaces': out, 'mine': File.objects.filter(employee=user).count(),
                         'can_link_records': user.can_finance() or user.has_role('hr_admin')})


@extend_schema(tags=['Drive'])
class BrowseView(APIView):
    """GET /api/drive/browse/?space=&folder= -- one folder's subfolders and files.
    Also ?q= (search everything readable), ?view=mine|recent, and link filters ?employee=&project=&transaction=&expense=&invoice=&statement=&fy=."""
    permission_classes = [IsEmployee]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user, p = request.user, request.query_params
        files = files_for(user).select_related('folder', 'uploaded_by', 'employee', 'project', 'transaction')
        links = {k: p[k] for k in LINK_FILTERS if p.get(k, '').isdigit()}
        folder = None
        payload = {'space': None, 'folder': None, 'folders': [], 'can_write': False, 'mode': 'folder'}
        if p.get('q') or links or p.get('view') or p.get('fy'):
            payload['mode'] = 'search'
            if p.get('space') in readable_spaces(user):
                files = files.filter(space=p['space'])
                payload['space'] = p['space']
            if p.get('q'):
                q = p['q'].strip()
                files = files.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(folder__name__icontains=q))
                folders = folders_for(user).filter(name__icontains=q)
                if payload['space']:
                    folders = folders.filter(space=payload['space'])
                payload['folders'] = FolderSerializer(with_counts(folders, user)[:30], many=True).data
            if links:
                files = files.filter(**{f'{k}_id': v for k, v in links.items()})
            if p.get('fy'):
                files = files.filter(Q(fiscal_year=p['fy']) | Q(folder__fiscal_year=p['fy']))
            if p.get('view') == 'mine':
                files = files.filter(employee=user)
            files = files.order_by('-created_at')[:200] if p.get('view') == 'recent' else files[:500]
        else:
            space = p.get('space') or Space.COMPANY
            if space not in readable_spaces(user):
                raise PermissionDenied('You cannot open this space.')
            if p.get('folder'):
                folder = get_object_or_404(folders_for(user).filter(space=space), pk=p['folder'])
            payload.update(space=space, can_write=can_write(user, space),
                           folder=FolderSerializer(folder).data if folder else None,
                           folders=FolderSerializer(with_counts(folders_for(user).filter(space=space, parent=folder), user), many=True).data)
            files = files.filter(space=space, folder=folder)
        payload['files'] = FileSerializer(files, many=True).data
        return Response(payload)


@extend_schema(tags=['Drive'])
class FolderViewSet(mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):
    permission_classes = [IsEmployee]
    serializer_class = FolderSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return with_counts(folders_for(self.request.user).select_related('parent'), self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if not can_delete(self.request.user, serializer.instance):
            raise PermissionDenied('Only the folder creator or HR can rename or move this folder.')
        serializer.save()

    def perform_destroy(self, folder):
        if not can_delete(self.request.user, folder):
            raise PermissionDenied('You cannot delete this folder.')
        if folder.children.exists() or folder.files.exists():
            raise ValidationError('Only empty folders can be deleted. Move or delete what is inside first.')
        folder.delete()

    @action(detail=True, methods=['get'])
    def zip(self, request, pk=None):
        folder = self.get_object()
        return zip_response(files_for(request.user).filter(folder_id__in=folder.descendant_ids()), folder.name, folder)


@extend_schema(tags=['Drive'])
class FileViewSet(mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                  viewsets.GenericViewSet):
    permission_classes = [IsEmployee]
    serializer_class = FileSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return files_for(self.request.user).select_related('folder', 'uploaded_by', 'employee', 'project', 'transaction')

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        if not can_delete(self.request.user, serializer.instance):
            raise PermissionDenied('Only the uploader or HR can change this file.')
        serializer.save()

    def perform_destroy(self, f):
        if not can_delete(self.request.user, f):
            raise PermissionDenied('Only the uploader or HR can delete this file.')
        f.delete()
        transaction.on_commit(lambda: f.file.delete(save=False))

    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        return serve_document(self.get_object(), download=request.query_params.get('download') == '1')


@extend_schema(tags=['Drive'])
class ShareLinkViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Expiring read-only links. DELETE revokes (the row is kept for the record)."""
    permission_classes = [IsEmployee]
    serializer_class = ShareLinkSerializer

    def get_queryset(self):
        user = self.request.user
        spaces = [s for s in readable_spaces(user) if can_share(user, s)]
        return ShareLink.objects.filter(Q(folder__space__in=spaces) | Q(file__space__in=spaces)).select_related(
            'folder', 'file', 'created_by')

    def perform_create(self, serializer):
        user = self.request.user
        target = serializer.validated_data.get('folder') or serializer.validated_data.get('file')
        visible = (folders_for(user) if isinstance(target, Folder) else files_for(user)).filter(pk=target.pk).exists()
        if not visible or not can_share(user, target.space):
            raise PermissionDenied('You cannot share this.')
        serializer.save(created_by=user)

    def perform_destroy(self, link):
        if not link.revoked_at:
            link.revoked_at = timezone.now()
            link.save(update_fields=['revoked_at'])


def shared_link(token):
    link = ShareLink.objects.select_related('folder', 'file', 'created_by').filter(token=token).first()
    if not link or link.revoked_at or link.expires_at <= timezone.now():
        raise Http404
    return link


def shared_files(link):
    # Never more than the person who made the link may see today (a later clearance downgrade narrows the link too).
    files = File.objects.filter(classification__lte=link.created_by.clearance)
    if link.file:
        return files.filter(pk=link.file_id)
    return files.filter(folder_id__in=link.folder.descendant_ids())


@extend_schema(tags=['Drive'])
class SharedView(APIView):
    """Public: GET /api/drive/shared/{token}/ lists what the link exposes; /files/{id}/ streams one file; /zip/ everything."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'drive_share'

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, token, file_id=None, as_zip=False):
        link = shared_link(token)
        files = shared_files(link).select_related('folder')
        if file_id:
            return serve_document(get_object_or_404(files, pk=file_id), download=request.query_params.get('download') == '1')
        if as_zip:
            return zip_response(files, link.folder.name if link.folder else 'shared', link.folder)
        base = len(link.folder.path()) if link.folder else 0
        return Response({
            'label': link.label, 'name': link.folder.name if link.folder else link.file.name,
            'expires_at': link.expires_at,
            'files': [{'id': f.pk, 'name': f.name, 'title': f.name, 'extension': f.extension, 'size': f.size,
                       'path': '/'.join((f.folder.path() if f.folder else [])[base:]), 'fiscal_year': f.fiscal_year,
                       'description': f.description, 'created_at': f.created_at,
                       'url': f'/api/drive/shared/{token}/files/{f.pk}/'} for f in files],
        })
