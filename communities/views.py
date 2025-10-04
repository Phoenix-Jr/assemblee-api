from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from datetime import date, timedelta
from .models import (
    Community, Pastor, Service, Ministry, Event,
    BibleStudy, Meditation, Testimony, Gallery, Member
)
from .serializers import (
    CommunityListSerializer, CommunityDetailSerializer,
    EventSerializer, MeditationSerializer, TestimonySerializer,
    MemberSerializer
)


class CommunityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les communautés
    """
    queryset = Community.objects.filter(is_active=True)
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'full_name', 'description', 'slogan']
    ordering_fields = ['founded_year', 'members_count', 'name']
    ordering = ['founded_year']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CommunityListSerializer
        return CommunityDetailSerializer
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, slug=None):
        """Obtenir les statistiques détaillées d'une communauté"""
        community = self.get_object()
        stats = {
            'members': {
                'total': community.members_count,
                'active': community.members.filter(is_active=True).count(),
                'new_this_month': community.members.filter(
                    join_date__gte=date.today() - timedelta(days=30)
                ).count()
            },
            'ministries': {
                'total': community.ministries.count(),
                'total_participants': sum(m.participants_count for m in community.ministries.all())
            },
            'events': {
                'upcoming': community.events.filter(date__gte=date.today()).count(),
                'this_month': community.events.filter(
                    date__month=date.today().month,
                    date__year=date.today().year
                ).count()
            },
            'baptisms': {
                'this_year': community.baptisms_current_year,
                'total': community.baptisms.filter(is_completed=True).count()
            }
        }
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def upcoming_events(self, request, slug=None):
        """Liste des prochains événements de la communauté"""
        community = self.get_object()
        events = community.events.filter(
            date__gte=date.today()
        ).order_by('date', 'start_time')[:10]
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def meditations(self, request, slug=None):
        """Méditations récentes de la communauté"""
        community = self.get_object()
        meditations = community.meditations.filter(
            is_published=True
        ).order_by('-published_date')[:10]
        serializer = MeditationSerializer(meditations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def testimonies(self, request, slug=None):
        """Témoignages de la communauté"""
        community = self.get_object()
        testimonies = community.testimonies.filter(
            is_published=True,
            is_verified=True
        ).order_by('-date')[:10]
        serializer = TestimonySerializer(testimonies, many=True)
        return Response(serializer.data)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les événements
    """
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['community', 'type', 'date']
    search_fields = ['title', 'description', 'organizer']
    ordering_fields = ['date', 'start_time']
    ordering = ['date', 'start_time']
    
    def get_queryset(self):
        queryset = Event.objects.all()
        
        # Filtrer par communauté si spécifié
        community_slug = self.request.query_params.get('community', None)
        if community_slug:
            queryset = queryset.filter(community__slug=community_slug)
        
        # Filtrer les événements futurs par défaut
        upcoming_only = self.request.query_params.get('upcoming', 'true')
        if upcoming_only.lower() == 'true':
            queryset = queryset.filter(date__gte=date.today())
        
        return queryset.select_related('community')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request, pk=None):
        """S'inscrire à un événement"""
        event = self.get_object()
        member = request.user.member
        
        if event.registration_required:
            # Vérifier le nombre maximum de participants
            if event.max_participants and event.registrations.count() >= event.max_participants:
                return Response(
                    {'detail': 'L\'événement est complet'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Créer l'inscription
            registration, created = EventRegistration.objects.get_or_create(
                event=event,
                member=member
            )
            
            if created:
                return Response({'detail': 'Inscription réussie'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'detail': 'Déjà inscrit'}, status=status.HTTP_200_OK)
        
        return Response(
            {'detail': 'Cet événement ne nécessite pas d\'inscription'},
            status=status.HTTP_400_BAD_REQUEST
        )


class MeditationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les méditations
    """
    serializer_class = MeditationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['community', 'type', 'category', 'author']
    search_fields = ['title', 'content', 'bible_verse']
    ordering_fields = ['published_date', 'duration_minutes']
    ordering = ['-published_date']
    
    def get_queryset(self):
        return Meditation.objects.filter(
            is_published=True
        ).select_related('community', 'author')


class TestimonyViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les témoignages
    """
    serializer_class = TestimonySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['community', 'category']
    search_fields = ['title', 'author_name', 'excerpt']
    ordering = ['-date']
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            # Pour la lecture, montrer seulement les témoignages publiés et vérifiés
            return Testimony.objects.filter(
                is_published=True,
                is_verified=True
            ).select_related('community')
        # Pour les autres actions (création), retourner tous
        return Testimony.objects.all()
    
    def perform_create(self, serializer):
        # Les nouveaux témoignages ne sont pas publiés par défaut
        serializer.save(is_published=False, is_verified=False)