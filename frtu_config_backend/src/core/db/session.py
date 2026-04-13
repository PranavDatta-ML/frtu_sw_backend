import asyncio
from src import Settings
from sqlalchemy.ext.asyncio import create_async_engine, async_scoped_session, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base


settings = Settings.get_settings()
Base = declarative_base()


class DatabaseSession:
    """
    DatabaseSession manages database connections and sessions for multiple binds.
    
    It allows for dynamically fetching session and engine instances based on the 
    bind key defined in the model class. The bind keys are specified in the models 
    using the `__bind_key__` attribute.
    """

    # Class variables to store session factories and engines for each bind
    _sessions = {}
    _engines = {}

    @classmethod
    def init(cls):
        """
        Initialize database connections and create session factories for all binds 
        defined in the settings. This method must be called once during app startup 
        to set up the session and engine mappings.
        """
        if cls._sessions:
            return

        # Initialize engines and sessions for each bind defined in settings
        cls.init_engines_and_sessions()

    @classmethod
    def init_engines_and_sessions(cls):
        for bind_key, conn_str in settings.DATABASE_BINDS.items():
            engine = create_async_engine(conn_str)
            cls._engines[bind_key] = engine
            session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            cls._sessions[bind_key] = async_scoped_session(session_factory, scopefunc=asyncio.current_task)

    @classmethod
    async def create_all(cls):
        """
        Create all tables in all databases corresponding to the defined binds.
        
        This method must be explicitly called in an asynchronous context to create tables.
        """
        for engine in cls._engines.values():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    @classmethod
    def get_session(cls, model):
        """
        Retrieve the session associated with the model's bind key.
        
        :param model: SQLAlchemy model class. The model should define `__bind_key__` 
                      to specify which bind to use. Defaults to 'default' bind if 
                      not defined.
        :return: Session instance corresponding to the model's bind key.
        """
        bind_key = getattr(model, '__bind_key__')
        return cls._sessions.get(bind_key)

    @classmethod
    def get_engine(cls, model):
        """
        Retrieve the engine associated with the model's bind key.
        
        :param model: SQLAlchemy model class. The model should define `__bind_key__` 
                      to specify which engine to use. Defaults to 'default' bind if 
                      not defined.
        :return: Engine instance corresponding to the model's bind key.
        """
        bind_key = getattr(model, '__bind_key__', 'default')
        return cls._engines.get(bind_key)

    @classmethod
    def close_session(cls, model):
        """
        Close the session associated with the model's bind key. 
        
        This method ensures that the session is properly removed, preventing session 
        leakage in threaded environments.
        
        :param model: SQLAlchemy model class. The model should define `__bind_key__` 
                      to specify which bind's session to close. Defaults to 'default' 
                      bind if not defined.
        """
        bind_key = getattr(model, '__bind_key__', 'default')
        session = cls._sessions.get(bind_key)
        if session:
            session.remove()


# Initializing the DatabaseSession
DatabaseSession.init()