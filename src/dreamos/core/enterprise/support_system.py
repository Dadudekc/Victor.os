"""
Victor.os Enterprise Support System
Phase 4: Enterprise Deployment - Support, training, and customer success
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logger = structlog.get_logger("support_system")

class TicketPriority(Enum):
    """Support ticket priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketStatus(Enum):
    """Support ticket status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketCategory(Enum):
    """Support ticket categories"""
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    TRAINING = "training"
    COMPLIANCE = "compliance"
    SECURITY = "security"

class SupportTier(Enum):
    """Support tiers"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class SupportTicket:
    """Support ticket information"""
    ticket_id: str
    tenant_id: str
    user_id: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    subject: str
    description: str
    created_at: float
    updated_at: float
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    tags: List[str] = None
    attachments: List[str] = None
    customer_satisfaction: Optional[int] = None

@dataclass
class TicketResponse:
    """Support ticket response"""
    response_id: str
    ticket_id: str
    user_id: str
    message: str
    timestamp: float
    is_internal: bool
    attachments: List[str] = None

@dataclass
class TrainingSession:
    """Training session information"""
    session_id: str
    tenant_id: str
    title: str
    description: str
    trainer_id: str
    scheduled_at: float
    duration_minutes: int
    max_participants: int
    participants: List[str]
    materials: List[str]
    status: str  # scheduled, in_progress, completed, cancelled
    recording_url: Optional[str] = None
    feedback_scores: List[int] = None

@dataclass
class KnowledgeBaseArticle:
    """Knowledge base article"""
    article_id: str
    title: str
    content: str
    category: str
    tags: List[str]
    author_id: str
    created_at: float
    updated_at: float
    views: int
    helpful_votes: int
    unhelpful_votes: int
    status: str  # draft, published, archived

class EnterpriseSupportSystem:
    """Enterprise support system for customer success"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.support_tickets: Dict[str, SupportTicket] = {}
        self.ticket_responses: Dict[str, List[TicketResponse]] = {}
        self.training_sessions: Dict[str, TrainingSession] = {}
        self.knowledge_base: Dict[str, KnowledgeBaseArticle] = {}
        self.support_agents: Dict[str, Dict[str, Any]] = {}
        
        # Setup support storage
        self.support_dir = Path("support")
        self.support_dir.mkdir(exist_ok=True)
        
        # Initialize support system
        self._initialize_support_system()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for support system"""
        return {
            "auto_assignment": True,
            "sla_response_times": {
                TicketPriority.LOW: 24 * 3600,      # 24 hours
                TicketPriority.MEDIUM: 8 * 3600,    # 8 hours
                TicketPriority.HIGH: 4 * 3600,      # 4 hours
                TicketPriority.CRITICAL: 1 * 3600   # 1 hour
            },
            "auto_escalation": True,
            "escalation_threshold_hours": 2,
            "customer_satisfaction_survey": True,
            "knowledge_base_enabled": True,
            "training_sessions_enabled": True,
            "support_hours": {
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC"
            }
        }
    
    def _initialize_support_system(self):
        """Initialize support system"""
        # Create support directories
        (self.support_dir / "tickets").mkdir(exist_ok=True)
        (self.support_dir / "training").mkdir(exist_ok=True)
        (self.support_dir / "knowledge_base").mkdir(exist_ok=True)
        (self.support_dir / "attachments").mkdir(exist_ok=True)
        
        # Initialize default support agents
        self._initialize_support_agents()
        
        # Initialize knowledge base
        self._initialize_knowledge_base()
    
    def _initialize_support_agents(self):
        """Initialize support agents"""
        default_agents = [
            {
                "agent_id": "agent_001",
                "name": "Sarah Johnson",
                "email": "sarah.johnson@victor.os",
                "specialties": ["technical", "billing"],
                "tier": SupportTier.ENTERPRISE,
                "active": True,
                "current_tickets": 0,
                "max_tickets": 10
            },
            {
                "agent_id": "agent_002",
                "name": "Mike Chen",
                "email": "mike.chen@victor.os",
                "specialties": ["technical", "security"],
                "tier": SupportTier.PREMIUM,
                "active": True,
                "current_tickets": 0,
                "max_tickets": 8
            },
            {
                "agent_id": "agent_003",
                "name": "Lisa Rodriguez",
                "email": "lisa.rodriguez@victor.os",
                "specialties": ["training", "compliance"],
                "tier": SupportTier.STANDARD,
                "active": True,
                "current_tickets": 0,
                "max_tickets": 6
            }
        ]
        
        for agent in default_agents:
            self.support_agents[agent["agent_id"]] = agent
    
    def _initialize_knowledge_base(self):
        """Initialize knowledge base with default articles"""
        default_articles = [
            {
                "title": "Getting Started with Victor.os",
                "content": "Welcome to Victor.os! This guide will help you get started...",
                "category": "onboarding",
                "tags": ["getting-started", "onboarding", "tutorial"]
            },
            {
                "title": "Agent Deployment Best Practices",
                "content": "Learn the best practices for deploying agents in your environment...",
                "category": "deployment",
                "tags": ["deployment", "agents", "best-practices"]
            },
            {
                "title": "Security and Compliance Overview",
                "content": "Understanding security features and compliance standards...",
                "category": "security",
                "tags": ["security", "compliance", "gdpr", "soc2"]
            }
        ]
        
        for i, article_data in enumerate(default_articles):
            article = KnowledgeBaseArticle(
                article_id=f"kb_{i+1:03d}",
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data["tags"],
                author_id="system",
                created_at=time.time(),
                updated_at=time.time(),
                views=0,
                helpful_votes=0,
                unhelpful_votes=0,
                status="published"
            )
            self.knowledge_base[article.article_id] = article
    
    def _start_background_tasks(self):
        """Start background support tasks"""
        asyncio.create_task(self._sla_monitoring_loop())
        asyncio.create_task(self._ticket_escalation_loop())
        asyncio.create_task(self._satisfaction_survey_loop())
        asyncio.create_task(self._knowledge_base_analytics_loop())
    
    async def create_support_ticket(self, tenant_id: str, user_id: str, category: TicketCategory,
                                  priority: TicketPriority, subject: str, description: str,
                                  tags: List[str] = None, attachments: List[str] = None) -> str:
        """Create a new support ticket"""
        try:
            ticket_id = f"TICKET_{uuid.uuid4().hex[:8].upper()}"
            
            ticket = SupportTicket(
                ticket_id=ticket_id,
                tenant_id=tenant_id,
                user_id=user_id,
                category=category,
                priority=priority,
                status=TicketStatus.OPEN,
                subject=subject,
                description=description,
                created_at=time.time(),
                updated_at=time.time(),
                tags=tags or [],
                attachments=attachments or []
            )
            
            self.support_tickets[ticket_id] = ticket
            self.ticket_responses[ticket_id] = []
            
            # Auto-assign ticket if enabled
            if self.config["auto_assignment"]:
                await self._auto_assign_ticket(ticket_id)
            
            logger.info("Support ticket created", 
                       ticket_id=ticket_id,
                       tenant_id=tenant_id,
                       category=category.value,
                       priority=priority.value)
            
            return ticket_id
            
        except Exception as e:
            logger.error("Failed to create support ticket", 
                        tenant_id=tenant_id,
                        error=str(e))
            raise
    
    async def _auto_assign_ticket(self, ticket_id: str):
        """Auto-assign ticket to available agent"""
        try:
            ticket = self.support_tickets[ticket_id]
            
            # Find available agents with matching specialties
            available_agents = []
            for agent_id, agent in self.support_agents.items():
                if (agent["active"] and 
                    agent["current_tickets"] < agent["max_tickets"] and
                    ticket.category.value in agent["specialties"]):
                    available_agents.append((agent_id, agent))
            
            if available_agents:
                # Sort by current ticket load and assign to least busy agent
                available_agents.sort(key=lambda x: x[1]["current_tickets"])
                selected_agent_id = available_agents[0][0]
                
                ticket.assigned_to = selected_agent_id
                self.support_agents[selected_agent_id]["current_tickets"] += 1
                
                logger.info("Ticket auto-assigned", 
                           ticket_id=ticket_id,
                           agent_id=selected_agent_id)
            
        except Exception as e:
            logger.error("Failed to auto-assign ticket", 
                        ticket_id=ticket_id,
                        error=str(e))
    
    async def add_ticket_response(self, ticket_id: str, user_id: str, message: str,
                                is_internal: bool = False, attachments: List[str] = None) -> str:
        """Add response to support ticket"""
        try:
            if ticket_id not in self.support_tickets:
                raise ValueError("Ticket not found")
            
            response_id = str(uuid.uuid4())
            
            response = TicketResponse(
                response_id=response_id,
                ticket_id=ticket_id,
                user_id=user_id,
                message=message,
                timestamp=time.time(),
                is_internal=is_internal,
                attachments=attachments or []
            )
            
            self.ticket_responses[ticket_id].append(response)
            
            # Update ticket status
            ticket = self.support_tickets[ticket_id]
            ticket.updated_at = time.time()
            
            if not is_internal:
                ticket.status = TicketStatus.WAITING_CUSTOMER
            else:
                ticket.status = TicketStatus.IN_PROGRESS
            
            logger.info("Ticket response added", 
                       ticket_id=ticket_id,
                       response_id=response_id,
                       is_internal=is_internal)
            
            return response_id
            
        except Exception as e:
            logger.error("Failed to add ticket response", 
                        ticket_id=ticket_id,
                        error=str(e))
            raise
    
    async def update_ticket_status(self, ticket_id: str, status: TicketStatus, resolution: str = None):
        """Update ticket status"""
        try:
            if ticket_id not in self.support_tickets:
                raise ValueError("Ticket not found")
            
            ticket = self.support_tickets[ticket_id]
            ticket.status = status
            ticket.updated_at = time.time()
            
            if resolution:
                ticket.resolution = resolution
            
            # If ticket is resolved/closed, free up agent
            if status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] and ticket.assigned_to:
                agent_id = ticket.assigned_to
                if agent_id in self.support_agents:
                    self.support_agents[agent_id]["current_tickets"] = max(0, 
                        self.support_agents[agent_id]["current_tickets"] - 1)
            
            logger.info("Ticket status updated", 
                       ticket_id=ticket_id,
                       status=status.value)
            
        except Exception as e:
            logger.error("Failed to update ticket status", 
                        ticket_id=ticket_id,
                        error=str(e))
            raise
    
    async def get_ticket_info(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive ticket information"""
        if ticket_id not in self.support_tickets:
            return None
        
        ticket = self.support_tickets[ticket_id]
        responses = self.ticket_responses.get(ticket_id, [])
        
        return {
            "ticket": asdict(ticket),
            "responses": [asdict(r) for r in responses],
            "response_count": len(responses),
            "sla_status": await self._check_sla_status(ticket),
            "agent_info": self.support_agents.get(ticket.assigned_to) if ticket.assigned_to else None
        }
    
    async def _check_sla_status(self, ticket: SupportTicket) -> Dict[str, Any]:
        """Check SLA status for ticket"""
        sla_time = self.config["sla_response_times"].get(ticket.priority, 24 * 3600)
        time_since_creation = time.time() - ticket.created_at
        
        return {
            "sla_hours": sla_time / 3600,
            "time_elapsed_hours": time_since_creation / 3600,
            "within_sla": time_since_creation <= sla_time,
            "overdue_hours": max(0, (time_since_creation - sla_time) / 3600)
        }
    
    async def create_training_session(self, tenant_id: str, title: str, description: str,
                                    trainer_id: str, scheduled_at: float, duration_minutes: int,
                                    max_participants: int, materials: List[str] = None) -> str:
        """Create a training session"""
        try:
            session_id = f"TRAINING_{uuid.uuid4().hex[:8].upper()}"
            
            session = TrainingSession(
                session_id=session_id,
                tenant_id=tenant_id,
                title=title,
                description=description,
                trainer_id=trainer_id,
                scheduled_at=scheduled_at,
                duration_minutes=duration_minutes,
                max_participants=max_participants,
                participants=[],
                materials=materials or [],
                status="scheduled",
                recording_url=None,
                feedback_scores=[]
            )
            
            self.training_sessions[session_id] = session
            
            logger.info("Training session created", 
                       session_id=session_id,
                       tenant_id=tenant_id,
                       title=title)
            
            return session_id
            
        except Exception as e:
            logger.error("Failed to create training session", 
                        tenant_id=tenant_id,
                        error=str(e))
            raise
    
    async def register_for_training(self, session_id: str, user_id: str) -> bool:
        """Register user for training session"""
        try:
            if session_id not in self.training_sessions:
                raise ValueError("Training session not found")
            
            session = self.training_sessions[session_id]
            
            if user_id in session.participants:
                return False  # Already registered
            
            if len(session.participants) >= session.max_participants:
                return False  # Session full
            
            session.participants.append(user_id)
            
            logger.info("User registered for training", 
                       session_id=session_id,
                       user_id=user_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to register for training", 
                        session_id=session_id,
                        user_id=user_id,
                        error=str(e))
            return False
    
    async def create_knowledge_base_article(self, title: str, content: str, category: str,
                                          author_id: str, tags: List[str] = None) -> str:
        """Create knowledge base article"""
        try:
            article_id = f"KB_{uuid.uuid4().hex[:8].upper()}"
            
            article = KnowledgeBaseArticle(
                article_id=article_id,
                title=title,
                content=content,
                category=category,
                tags=tags or [],
                author_id=author_id,
                created_at=time.time(),
                updated_at=time.time(),
                views=0,
                helpful_votes=0,
                unhelpful_votes=0,
                status="draft"
            )
            
            self.knowledge_base[article_id] = article
            
            logger.info("Knowledge base article created", 
                       article_id=article_id,
                       title=title)
            
            return article_id
            
        except Exception as e:
            logger.error("Failed to create knowledge base article", error=str(e))
            raise
    
    async def search_knowledge_base(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """Search knowledge base articles"""
        try:
            results = []
            query_lower = query.lower()
            
            for article in self.knowledge_base.values():
                if article.status != "published":
                    continue
                
                if category and article.category != category:
                    continue
                
                # Simple text search
                if (query_lower in article.title.lower() or 
                    query_lower in article.content.lower() or
                    any(query_lower in tag.lower() for tag in article.tags)):
                    
                    results.append({
                        "article_id": article.article_id,
                        "title": article.title,
                        "category": article.category,
                        "tags": article.tags,
                        "views": article.views,
                        "helpful_votes": article.helpful_votes,
                        "relevance_score": self._calculate_relevance_score(query, article)
                    })
            
            # Sort by relevance score
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return results[:10]  # Return top 10 results
            
        except Exception as e:
            logger.error("Knowledge base search failed", error=str(e))
            return []
    
    def _calculate_relevance_score(self, query: str, article: KnowledgeBaseArticle) -> float:
        """Calculate relevance score for search results"""
        score = 0.0
        query_lower = query.lower()
        
        # Title match (highest weight)
        if query_lower in article.title.lower():
            score += 10.0
        
        # Content match
        if query_lower in article.content.lower():
            score += 5.0
        
        # Tag match
        for tag in article.tags:
            if query_lower in tag.lower():
                score += 3.0
        
        # Popularity bonus
        score += min(article.views / 100, 2.0)  # Max 2 points for popularity
        score += min(article.helpful_votes / 10, 1.0)  # Max 1 point for helpful votes
        
        return score
    
    async def _sla_monitoring_loop(self):
        """Background SLA monitoring loop"""
        while True:
            try:
                current_time = time.time()
                
                for ticket_id, ticket in self.support_tickets.items():
                    if ticket.status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]:
                        sla_status = await self._check_sla_status(ticket)
                        
                        if not sla_status["within_sla"]:
                            logger.warning("SLA violation detected", 
                                          ticket_id=ticket_id,
                                          overdue_hours=sla_status["overdue_hours"])
                            
                            # Auto-escalate if enabled
                            if self.config["auto_escalation"]:
                                await self._escalate_ticket(ticket_id)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error("SLA monitoring error", error=str(e))
                await asyncio.sleep(300)
    
    async def _escalate_ticket(self, ticket_id: str):
        """Escalate ticket to higher priority"""
        try:
            ticket = self.support_tickets[ticket_id]
            
            # Increase priority
            priority_order = [TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH, TicketPriority.CRITICAL]
            current_index = priority_order.index(ticket.priority)
            
            if current_index < len(priority_order) - 1:
                ticket.priority = priority_order[current_index + 1]
                ticket.updated_at = time.time()
                
                logger.info("Ticket escalated", 
                           ticket_id=ticket_id,
                           new_priority=ticket.priority.value)
            
        except Exception as e:
            logger.error("Failed to escalate ticket", 
                        ticket_id=ticket_id,
                        error=str(e))
    
    async def _ticket_escalation_loop(self):
        """Background ticket escalation loop"""
        while True:
            try:
                current_time = time.time()
                escalation_threshold = self.config["escalation_threshold_hours"] * 3600
                
                for ticket_id, ticket in self.support_tickets.items():
                    if (ticket.status == TicketStatus.OPEN and 
                        current_time - ticket.updated_at > escalation_threshold):
                        
                        await self._escalate_ticket(ticket_id)
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error("Ticket escalation error", error=str(e))
                await asyncio.sleep(3600)
    
    async def _satisfaction_survey_loop(self):
        """Background satisfaction survey loop"""
        if not self.config["customer_satisfaction_survey"]:
            return
        
        while True:
            try:
                # Find resolved tickets without satisfaction scores
                for ticket_id, ticket in self.support_tickets.items():
                    if (ticket.status == TicketStatus.RESOLVED and 
                        ticket.customer_satisfaction is None):
                        
                        # In real implementation, send survey email
                        logger.info("Satisfaction survey due", ticket_id=ticket_id)
                
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                logger.error("Satisfaction survey error", error=str(e))
                await asyncio.sleep(86400)
    
    async def _knowledge_base_analytics_loop(self):
        """Background knowledge base analytics loop"""
        while True:
            try:
                # Update article popularity metrics
                for article in self.knowledge_base.values():
                    # Simulate view increases
                    if article.status == "published":
                        article.views += 1
                
                await asyncio.sleep(3600)  # Update hourly
                
            except Exception as e:
                logger.error("Knowledge base analytics error", error=str(e))
                await asyncio.sleep(3600)
    
    async def get_support_metrics(self, tenant_id: str = None) -> Dict[str, Any]:
        """Get support system metrics"""
        try:
            tickets = self.support_tickets.values()
            if tenant_id:
                tickets = [t for t in tickets if t.tenant_id == tenant_id]
            
            total_tickets = len(tickets)
            open_tickets = len([t for t in tickets if t.status == TicketStatus.OPEN])
            resolved_tickets = len([t for t in tickets if t.status == TicketStatus.RESOLVED])
            
            # Calculate average resolution time
            resolved_times = []
            for ticket in tickets:
                if ticket.status == TicketStatus.RESOLVED:
                    # Find resolution response
                    responses = self.ticket_responses.get(ticket.ticket_id, [])
                    if responses:
                        resolution_time = responses[-1].timestamp - ticket.created_at
                        resolved_times.append(resolution_time)
            
            avg_resolution_time = sum(resolved_times) / len(resolved_times) if resolved_times else 0
            
            return {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "resolved_tickets": resolved_tickets,
                "resolution_rate": (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0,
                "avg_resolution_time_hours": avg_resolution_time / 3600,
                "active_agents": len([a for a in self.support_agents.values() if a["active"]]),
                "training_sessions": len(self.training_sessions),
                "knowledge_base_articles": len(self.knowledge_base)
            }
            
        except Exception as e:
            logger.error("Failed to get support metrics", error=str(e))
            return {}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get support system status"""
        return {
            "total_tickets": len(self.support_tickets),
            "open_tickets": len([t for t in self.support_tickets.values() if t.status == TicketStatus.OPEN]),
            "active_agents": len([a for a in self.support_agents.values() if a["active"]]),
            "training_sessions": len(self.training_sessions),
            "knowledge_base_articles": len(self.knowledge_base),
            "config": {
                "auto_assignment": self.config["auto_assignment"],
                "auto_escalation": self.config["auto_escalation"],
                "customer_satisfaction_survey": self.config["customer_satisfaction_survey"],
                "knowledge_base_enabled": self.config["knowledge_base_enabled"],
                "training_sessions_enabled": self.config["training_sessions_enabled"]
            }
        } 