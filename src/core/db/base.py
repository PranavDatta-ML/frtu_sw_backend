from sqlalchemy.future import select
from sqlalchemy import text
from sqlalchemy import insert
from sqlalchemy import update
from sqlalchemy import delete
from sqlalchemy import bindparam
from sqlalchemy import and_, or_
from sqlalchemy.orm.exc import NoResultFound

from src import log
from src.core.db.session import DatabaseSession
from src.core.db.session import Base


class ModelAdmin:
    """
    ModelAdmin provides basic CRUD (Create, Read, Update, Delete) operations
    for SQLAlchemy models, along with methods to serialize model instances to 
    dictionaries.

    This class serves as a base for model administration, allowing for 
    consistent handling of database operations with logging and error handling.
    """

    def as_dict(self):
        """
        Convert the model instance to a dictionary representation.

        Date fields are converted to string format for serialization.

        :return: Dictionary representation of the model instance.
        """
        detail = {}
        for col in self.__tablename__.columns:
            if str(col.type).lower().startswith('date'):
                detail[col.name] = str(getattr(self, col.name))
            else:
                detail[col.name] = getattr(self, col.name)

        return detail

    @classmethod
    async def insert(cls, extra={}, **kwargs):
        """
        Insert a new record into the database.

        :param extra: Additional parameters for logging purposes.
        :param kwargs: Column values to be inserted into the record.
        :raises Exception: Raises an exception if the insert fails.
        :return: The current session after the insert operation.
        """
        session = DatabaseSession.get_session(cls)
        query = insert(cls).values(**kwargs).returning(*cls.__table__.c)
        try:
            log.info(f'Insert query with attrs={str(kwargs)} extra={str(extra)}')
            result = await session.execute(query)
            await session.commit()
            return cls(**result.fetchone()._asdict())
        except Exception as e:
            await session.rollback()
            log.error(f'Failed insert query due to error={str(e)} in {cls.__class__.__name__} '
                      f'with attrs={str(kwargs)} extra={str(extra)}')
            raise Exception(str(e))

    @classmethod
    async def bulk_insert(cls, records, extra={}):
        """
        Insert multiple records into the database.

        :param records: A list of dictionaries containing column values to be inserted.
        :param extra: Additional parameters for logging purposes.
        :raises Exception: Raises an exception if the bulk insert fails.
        :return: The current session after the bulk insert operation.
        """
        session = DatabaseSession.get_session(cls)
        query = insert(cls).values(records).returning(*cls.__table__.c)
        try:
            result = await session.execute(query)
            await session.commit()
            log.info(f'Bulk insert query with {str(len(records))} records successful extra={str(extra)}')
            return [cls(**row._asdict()) for row in result]
        except Exception as e:
            await session.rollback()
            log.error(f'Failed bulk insert due to error={str(e)} in {cls.__class__.__name__} '
                      f'with records={str(records)} extra={str(extra)}')
            raise Exception(str(e))

    @classmethod
    async def update(cls, extra={}, conditions={}, **kwargs):
        """
        Update existing records in the database based on specified conditions.

        :param extra: Additional parameters for logging purposes.
        :param conditions: A dictionary of conditions to filter which records to update.
        :param kwargs: Column values to be updated in the record.
        :raises NoResultFound: Raises if no records match the conditions.
        :raises Exception: Raises an exception if the update fails.
        :return: The current session after the update operation.
        """
        session = DatabaseSession.get_session(cls)
        filters = []
        if len(conditions):
            for column, value in conditions.items():
                column_obj = getattr(cls, column)
                if isinstance(value, str) and column_obj.type.__class__.__name__ == 'VARCHAR':
                    # Ensure the value is treated as a string for VARCHAR columns
                    filters.append((column_obj == str(value)))
                else:
                    # For other types, do the comparison as is
                    filters.append((column_obj == value))

        query = update(cls).where(and_(*filters)).values(**kwargs)
        try:
            log.info(f'Update query with attrs={str(kwargs)} extra={str(extra)}')
            await session.execute(query)
            await session.commit()
        except NoResultFound:
            await session.rollback()
            raise NoResultFound('No result found')
        except Exception as e:
            await session.rollback()
            log.error(f'Failed update query due to error={str(e)} in {cls.__class__.__name__} '
                      f'with attrs={str(kwargs)} extra={str(extra)}')
            raise e
        return session

    @classmethod
    async def bulk_update(cls, updates, conditions, extra={}):
        """
        Bulk update multiple records in the database based on specified conditions.

        :param updates: A list of dictionaries containing column values to be updated.
        :param conditions: A list of dictionaries of conditions for filtering records to update.
        :param extra: Additional parameters for logging purposes.
        :raises Exception: Raises an exception if the bulk update fails.
        :return: The current session after the bulk update operation.
        """
        session = DatabaseSession.get_session(cls)
        try:
            for update_values, condition in zip(updates, conditions):
                filters = []
                for column in condition:
                    filters.append((getattr(cls, column) == condition[column]))

                query = update(cls).where(and_(*filters)).values(**update_values)
                log.info(
                    f'Bulk update query with attrs={str(update_values)} conditions={str(condition)} extra={str(extra)}')
                await session.execute(query)

            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error(f'Failed bulk update due to error={str(e)} extra={str(extra)}')
            raise Exception(str(e))
        return session

    # @classmethod
    # async def select(cls, extra={}, columns=['*'], use_or=False, **conditions):
    #     """
    #     Retrieve records from the database based on specified conditions, including support for 'IN', '>', '<', '>=', and '<=' queries.

    #     :param extra: Additional parameters for logging purposes.
    #     :param columns: Specific columns to select from the model.
    #     :param conditions: A dictionary of conditions to filter which records to retrieve.
    #                     - Use '__gt', '__gte', '__lt', '__lte' for comparison operators.
    #                     - If the value is a list, an 'IN' query will be performed.
    #     :raises NoResultFound: Raises if no records match the conditions.
    #     :raises Exception: Raises an exception if the select fails.
    #     :return: List of records matching the conditions.

    #     Args:
    #         use_or:
    #     """
    #     session = DatabaseSession.get_session(cls)

    #     # Mapping of suffixes to SQLAlchemy filter operations
    #     operator_mapping = {
    #         '__gt': lambda col, val: col > val,
    #         '__gte': lambda col, val: col >= val,
    #         '__lt': lambda col, val: col < val,
    #         '__lte': lambda col, val: col <= val,
    #     }

    #     filters = []

    #     for column, value in conditions.items():
    #         # Handle comparison operators based on suffix
    #         for suffix, operation in operator_mapping.items():
    #             if column.endswith(suffix):
    #                 column_name = column[:-len(suffix)]  # Remove suffix to get actual column name
    #                 filters.append(operation(getattr(cls, column_name), value))
    #                 break
    #         else:
    #             # Handle 'IN' query if the value is a list
    #             if isinstance(value, list):
    #                 filters.append(getattr(cls, column).in_(value))
    #             # Default to equality
    #             else:
    #                 filters.append(getattr(cls, column) == value)

    #     try:
    #         log.info(f'Select query with attrs={str(conditions)} extra={str(extra)}')
    #         if filters:
    #             where_clause = or_(*filters) if use_or else and_(*filters)
    #             query = select(cls).with_only_columns(*columns).where(where_clause)
    #         else:
    #             query = select(cls).with_only_columns(*columns)

    #         log.info(f'Executing SQL: {str(query.compile(compile_kwargs={"literal_binds": True}))}')

    #         data = await session.execute(query)
    #         result = data.mappings().all()
    #         return result
    #     except Exception as e:
    #         log.error(f'Failed select query due to error={str(e)} extra={str(extra)}')
    #         await session.rollback()
    #         raise e

    @classmethod
    async def select(cls, extra={}, columns=None, use_or=False, **conditions):
        session = DatabaseSession.get_session(cls)

        try:
            log.info(f"Select query with attrs={str(conditions)} extra={str(extra)}")

            filters = []
            for col_name, value in conditions.items():
                col = getattr(cls, col_name)
                if isinstance(value, list):
                    filters.append(col.in_(value))
                else:
                    filters.append(col == value)

            where_clause = or_(*filters) if (use_or and filters) else and_(*filters)

            if columns:
                # Select specific columns
                query = select(*[getattr(cls, c) for c in columns]).where(where_clause)
            else:
                # Select ORM objects (correct behavior)
                query = select(cls).where(where_clause)

            log.info(
                f"Executing SQL: {str(query.compile(compile_kwargs={'literal_binds': True}))}"
            )

            result = await session.execute(query)

            # If selecting full ORM models
            if columns is None:
                return result.scalars().all()

            # If selecting specific columns
            return result.mappings().all()

        except Exception as e:
            log.error(f"Failed select query due to error={str(e)} extra={str(extra)}")
            await session.rollback()
            raise e


    @classmethod
    async def delete(cls, extra={}, conditions={}):
        """
        Delete records from the database based on specified conditions.

        :param extra: Additional parameters for logging purposes.
        :param conditions: A dictionary of conditions to filter which records to delete.
        :raises NoResultFound: Raises if no records match the conditions.
        :raises Exception: Raises an exception if the delete fails.
        :return: The current session after the delete operation.
        """
        session = DatabaseSession.get_session(cls)

        filters = []

        if len(conditions):
            for column in conditions:
                filters.append((getattr(cls, column) == f'{conditions[column]}'))

        query = delete(cls).where(and_(*filters))
        try:
            log.info(f'Delete query extra={str(extra)}')
            await session.execute(query)
            await session.commit()
        except NoResultFound:
            await session.rollback()
            raise NoResultFound('No result found')
        except Exception as e:
            log.error(f'Failed to delete due to error={str(e)} extra={str(extra)}')
            await session.rollback()
            raise Exception(str(e))
        return session
