from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Create database connection
DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(100))
    is_active = Column(Boolean, default=True)
    
    # İlişki kurma (User ile UserProfile arasında)
    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    learning_purpose = Column(String(50))  # Konuşma, yazma, dinleme, okuma
    daily_minutes = Column(Integer)  # Günlük kaç dakika
    created_at = Column(String(50))  # Profil oluşturma tarihi
    
    # İlişki kurma (UserProfile ile User arasında)
    user = relationship("User", back_populates="profile")

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    description = Column(Text, nullable=True)
    
class UserActivity(Base):
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_type = Column(String(50))  # konuşma, yazma, dinleme, okuma, vs.
    duration = Column(Integer)  # Dakika cinsinden
    notes = Column(Text, nullable=True)
    completed_at = Column(String(50))  # Tarih
    
    # İlişki
    user = relationship("User", backref="activities")

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)
    
# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 