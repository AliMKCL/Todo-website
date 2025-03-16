from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

#User table currently useless since project is designed for only one user, can be configured to maintain relationships between tables.
class User(Base):           
    __tablename__ = "users"  
    id = Column(Integer, primary_key=True) 
    name = Column(String, nullable=False) 
    email = Column(String, nullable=False, unique=True) 
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan") 
    

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True) 
    category = Column(String(50), nullable=False) 
    description = Column(String)
    priority = Column(Integer)
    due_date = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="tasks")

class DailyTask(Base):
    __tablename__ = "daily_tasks"  # Table for daily tasks
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, nullable=True)


