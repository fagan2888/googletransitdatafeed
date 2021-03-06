import problems as problems_module

class Persistable:

  def __init__(self, cursor_factory):
    """cursor_factory is an object with a 'cursor()' method that
       returns a database cursor"""

    self._cursor_factory = cursor_factory 
    self._rowid = None

  def cursor(self):
    if self._cursor_factory is None:
      raise Exception( "This object does not reference a database" )

    return self._cursor_factory.cursor()

  @classmethod
  def create_table(cls, cursor):
    fields_spec = ",".join(["%s %s"%(fn,ftype) for fn,ftype in cls._SQL_FIELDS])
    cursor.execute("""CREATE TABLE %s (%s);"""%(cls._SQL_TABLENAME,
                                                    fields_spec))
  @classmethod
  def create_indices(cls, cursor):
    if not hasattr( cls, "_SQL_INDEXABLE_FIELDS" ):
      return

    for fn in cls._SQL_INDEXABLE_FIELDS:
      cursor.execute("""CREATE INDEX %s_index ON %s (%s);"""%(fn,
                                                              cls._SQL_TABLENAME,
                                                              fn))

  def GetSqlValuesTuple(self, **extra_fields):
    """Return a tuple that outputs a row of _FIELD_NAMES to be written to a
       SQLite database.

    Arguments:
        extra_fields: a dictionary of fields that you would like to add or
                      override when constructing the tuple. For example, 
                      the StopTime class does not have an attribute 'trip_id'
                      but it is nevertheless a SQL field - it would be prudent
                      to include it in extra_fields.
    """

    result = []
    for fn, ftype in self._SQL_FIELDS:
      if fn in extra_fields:
        result.append(extra_fields[fn])
      else:
        # Since we'll be writting to SQLite, we want empty values to be
        # outputted as NULL string (contrary to what happens in
        # GetFieldValuesTuple)
        result.append(getattr(self, fn))
    return tuple(result)

  def save(self, **extra_fields):
    insert_query = "INSERT INTO %s (%s) VALUES (%s);" % (
       self._SQL_TABLENAME,
       ','.join([fn for fn, ft in self._SQL_FIELDS]),
       ','.join(['?'] * len(self._SQL_FIELDS)))

    cursor = self.cursor()
    cursor.execute( 
        insert_query, self.GetSqlValuesTuple(**extra_fields))

    self._rowid = cursor.lastrowid

  def update( self, **fields ):
    #TODO unit test

    field_setters = ", ".join( ["%s=?"%k for k in fields.keys()] ) 
    query = "UPDATE %s SET %s WHERE rowid=%s" % (
         self._SQL_TABLENAME,
	field_setters,
	self._rowid )

    cursor = self.cursor()
    cursor.execute( query, fields.values() )
  
  @classmethod
  def delete( cls, cursor, tolerant=False, **fields ):
    where_clause = " and ".join( ["%s=?"%k for k in fields.keys()] )
    query = "DELETE FROM stop_times WHERE "+where_clause
    cursor.execute( query, fields.values() )

    if not tolerant and  cursor.rowcount == 0:
      raise problems_module.Error, 'Attempted deletion of object which does not exist'

  @classmethod
  def select( cls, cursor, **fields ):
    where_clause = " and ".join( ["%s=?"%k for k in fields.keys()] )

    query = "SELECT * FROM "+cls._SQL_TABLENAME
    if where_clause != "":
      query += where_clause

    cursor.execute( query, fields.values() )

    sql_field_names = [fn for fn,ft in cls._SQL_FIELDS]
    for row in cursor:
      yield cls( field_dict=dict( zip( sql_field_names, row ) ) )
