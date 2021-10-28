
import asm3.al
import asm3.audit
import asm3.cachemem
import asm3.cachedisk
import asm3.i18n
import asm3.utils

import datetime
import sys
import time

from asm3.sitedefs import DB_TYPE, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME, DB_HAS_ASM2_PK_TABLE, DB_EXEC_LOG, DB_EXPLAIN_QUERIES, DB_TIME_QUERIES, DB_TIME_LOG_OVER, DB_TIMEOUT, CACHE_COMMON_QUERIES

class ResultRow(dict):
    """
    A ResultRow object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`. 
    It's also case insensitive as dbms tend to be on column names.
    """
    def copy(self):
        return ResultRow(dict.copy(self))

    def __getattr__(self, key):
        try:
            return self[key.upper()]
        except KeyError as k:
            raise AttributeError(k)

    def __setattr__(self, key, value):
        self[key.upper()] = value

    def __delattr__(self, key):
        try:
            del self[key.upper()]
        except KeyError as k:
            raise AttributeError(k)

    def __repr__(self):
        return '<ResultRow ' + dict.__repr__(self) + '>'

class QueryBuilder(object):
    """
    Build a query from component parts, keeping track of params eg:

    qb.select("animalname, sheltercode", "animal a")
    qb.leftjoin("adoption", "adoption.AnimalID = a.ID")
    qb.where("id", 5)
    qb.like("animalname", "bob")
    qb.orderby("animalname")

    dbo.query(qb.sql(), qb.params())
    """
    sselect = ""
    sfrom = ""
    sjoins = ""
    swhere = ""
    sorderby = ""
    values = []
    dbo = None
    
    def __init__(self, dbo):
        self.dbo = dbo
    
    def select(self, s, fromclause = ""):
        if s.lower().startswith("select"):
            self.sselect = s
        else:
            self.sselect = "SELECT %s"
        if fromclause != "":
            self.sfrom = " FROM %s " % fromclause
    
    def innerjoin(self, table, cond):
        self.sjoins += "INNER JOIN %s ON %s " % (table, cond)
    
    def leftjoin(self, table, cond):
        self.sjoins += "LEFT OUTER JOIN %s ON %s " % (table, cond)
    
    def where(self, k, v = "", cond = "and", operator = "="):
        """ If only one param is given, it is treated as a clause by itself """
        if self.swhere != "":
            self.swhere += " %s " % cond
        else:
            self.swhere = " WHERE "
        if v == "":
            self.swhere += k + " "
        else:
            self.swhere += "%s %s ? " % (k, operator)
            self.values.append(v)
    
    def like(self, k, v, cond = "and"):
        self.where("LOWER(%s)" % k, "%%%s%%" % v.lower(), cond, "LIKE")
    
    def orderby(self, s):
        self.sorderby = " ORDER BY %s" % s
    
    def sql(self):
        return self.sselect + " " + self.sfrom + self.sjoins + self.swhere + self.sorderby
    
    def params(self):
        return self.values

class Database(object):
    """
    Object that handles all interactions with the database.
    sitedefs.py supplies the default database connection info.
    This is the base class for all RDBMS provider specific functionality.
    """
    dbtype = DB_TYPE 
    host = DB_HOST
    port = DB_PORT
    username = DB_USERNAME
    password = DB_PASSWORD
    database = DB_NAME

    alias = "" 
    locale = "en"
    timezone = 0
    timezone_dst = False
    installpath = ""
    locked = False

    has_asm2_pk_table = DB_HAS_ASM2_PK_TABLE
    is_large_db = False
    timeout = DB_TIMEOUT
    connection = None

    type_shorttext = "VARCHAR(1024)"
    type_longtext = "TEXT"
    type_clob = "TEXT"
    type_datetime = "TIMESTAMP"
    type_integer = "INTEGER"
    type_float = "REAL"

    def connect(self):
        """ Virtual: Connect to the database and return the connection """
        raise NotImplementedError()

    def cursor_open(self):
        """ Returns a tuple containing an open connection and cursor.
            If the dbo object contains an active connection, we'll just use
            that to get a cursor to save time.
        """
        if self.connection is not None:
            c = self.connection
            s = self.connection.cursor()
        else:
            c = self.connect()
            s = c.cursor()
        return c, s

    def cursor_close(self, c, s):
        """ Closes a connection and cursor pair. If self.connection exists, then
            c must be it, so don't close it. Connection caching in this object
            is done by processes called via cron.py as they do not use pooling.
        """
        try:
            s.close()
        except:
            pass
        if self.connection is None:
            try:
                c.close()
            except:
                pass

    def ddl_add_column(self, table, column, coltype):
        return "ALTER TABLE %s ADD %s %s" % (table, column, coltype)

    def ddl_add_index(self, name, table, column, unique = False, partial = False):
        u = ""
        if unique: u = "UNIQUE "
        return "CREATE %sINDEX %s ON %s (%s)" % (u, name, table, column)

    def ddl_add_sequence(self, table, startat):
        return "" # Not all RDBMSes support sequences so don't do anything by default

    def ddl_add_table(self, name, fieldblock):
        return "CREATE TABLE %s (%s)" % (name, fieldblock)

    def ddl_add_table_column(self, name, coltype, nullable = True, pk = False):
        nullstr = "NOT NULL"
        if nullable: nullstr = "NULL"
        pkstr = ""
        if pk: pkstr = " PRIMARY KEY"
        return "%s %s %s%s" % ( name, coltype, nullstr, pkstr )

    def ddl_add_view(self, name, sql):
        return "CREATE VIEW %s AS %s" % (name, sql)

    def ddl_drop_column(self, table, column):
        return "ALTER TABLE %s DROP COLUMN %s" % (table, column)

    def ddl_drop_index(self, name, table):
        return "DROP INDEX %s" % name

    def ddl_drop_sequence(self, table):
        return "" # Not all RDBMSes support sequences so don't do anything by default

    def ddl_drop_view(self, name):
        return "DROP VIEW IF EXISTS %s" % name

    def ddl_modify_column(self, table, column, newtype, using = ""):
        return "" # Not all providers support this

    def encode_str_before_write(self, values):
        """ Fix and encode/decode any string values before storing them in the database.
            string column names with an asterisk will not do XSS escaping.
        """
        def transform(s):
            """ Transforms values going into the database """
            if s is None: return ""
            s = s.replace("`", "&bt;") # Encode backticks as they're going to become apostrophes
            s = s.replace("'", "`") # Compatibility with ASM2, turn apostrophes into backticks
            return s

        for k, v in values.copy().items(): # Work from a copy to prevent iterator problems
            if asm3.utils.is_str(v):
                if k.find("*") != -1:
                    # If there's an asterisk in the name, remove it so that the
                    # value is stored again below, but without XSS escaping
                    del values[k]
                    k = k.replace("*", "")
                else:
                    # Otherwise, do XSS escaping
                    v = self.escape_xss(v)
                # Any transformations before storing in the database
                v = transform(v)
                values[k] = "%s" % v
        return values

    def encode_str_after_read(self, v):
        """
        Encodes any string values returned by a query result.
        If v is a str, re-encodes it as an ascii str with HTML entities
        If it is any other type, returns v untouched
        """
        def transform(s):
            """ Transforms values coming out of the database """
            if s is None: return ""
            s = s.replace("`", "'") # Backticks become apostrophes again
            s = s.replace("&bt;", "`") # Encoded backticks become proper backticks
            return s

        try:
            if v is None: 
                return v
            elif asm3.utils.is_str(v): 
                return transform(v)
            else:
                return v
        except Exception as err:
            asm3.al.error(str(err), "Database.encode_str_after_read", self, sys.exc_info())
            raise err

    def escape(self, s):
        """ Makes a string value safe for database queries
            If available, dbms implementations should override this and use whatever 
            is available in the driver.
        """
        if s is None: return ""
        # This is historic - ASM2 switched backticks for apostrophes so we do for compatibility
        s = s.replace("'", "`")
        return s

    def escape_xss(self, s):
        """ XSS escapes a string """
        return s.replace("<", "&lt;").replace(">", "&gt;")

    def execute(self, sql, params=None, override_lock=False):
        """
            Runs the action query given and returns rows affected
            override_lock: if this is set to False and dbo.locked = True,
                           we don't do anything. This makes it easy to 
                           lock the database for writes, but keep databases 
                           up to date.
        """
        if not override_lock and self.locked: return 0
        if sql is None or sql.strip() == "": return 0
        try:
            c, s = self.cursor_open()
            if params:
                sql = self.switch_param_placeholder(sql)
                s.execute(sql, params)
            else:
                s.execute(sql)
            rv = s.rowcount
            c.commit()
            self.cursor_close(c, s)
            self._log_sql(sql, params)
            return rv
        except Exception as err:
            asm3.al.error(str(err), "Database.execute", self, sys.exc_info())
            asm3.al.error("failing sql: %s %s" % (sql, params), "Database.execute", self)
            try:
                # An error can leave a connection in unusable state, 
                # rollback any attempted changes.
                c.rollback()
            except:
                pass
            raise err
        finally:
            try:
                self.cursor_close(c, s)
            except:
                pass

    def execute_dbupdate(self, sql, params=None):
        """
        Runs an action query for a dbupdate script (sets override_lock
        to True so we don't forget)
        """
        return self.execute(sql, params=params, override_lock=True)

    def execute_many(self, sql, params=(), override_lock=False):
        """
            Runs the action query given with a list of tuples that contain
            substitution parameters. Eg:
            "INSERT INTO table (field1, field2) VALUES (%s, %s)", [ ( "val1", "val2" ), ( "val3", "val4" ) ]
            Returns rows affected
            override_lock: if this is set to False and dbo.locked = True,
                           we don't do anything. This makes it easy to lock the database
                           for writes, but keep databases upto date.
        """
        if not override_lock and self.locked: return
        if sql is None or sql.strip() == "": return 0
        try:
            c, s = self.cursor_open()
            sql = self.switch_param_placeholder(sql)
            s.executemany(sql, params)
            rv = s.rowcount
            c.commit()
            self.cursor_close(c, s)
            return rv
        except Exception as err:
            asm3.al.error(str(err), "Database.execute_many", self, sys.exc_info())
            asm3.al.error("failing sql: %s %s" % (sql, params), "Database.execute_many", self)
            try:
                # An error can leave a connection in unusable state, 
                # rollback any attempted changes.
                c.rollback()
            except:
                pass
            raise err
        finally:
            try:
                self.cursor_close(c, s)
            except:
                pass

    def first_row(self, rows, valueIfEmpty=None):
        """ Returns the first row in rows or valueIfEmpty if rows has no elements """
        if len(rows) == 0: return valueIfEmpty
        return rows[0]

    def get_id(self, table):
        """ Returns the next ID for a table """
        nextid = self.get_id_cache(table)
        self.update_asm2_primarykey(table, nextid)
        asm3.al.debug("get_id: %s -> %d (cache_pk)" % (table, nextid), "Database.get_id", self)
        return nextid

    def get_id_cache(self, table):
        """ Returns the next ID for a table using an in-memory cache. """
        cache_key = "%s_pk_%s" % (self.database, table)
        id = asm3.cachemem.increment(cache_key)
        if id is None:
            id = self.get_id_max(table)
            asm3.cachemem.put(cache_key, id, 86400)
        return id

    def get_id_max(self, table):
        """ Returns the next ID for a table using MAX(ID) """
        return self.query_int("SELECT MAX(ID) FROM %s" % table) + 1

    def get_query_builder(self):
        return QueryBuilder(self)

    def get_recordversion(self):
        """
        Returns an integer representation of now for use in the RecordVersion
        column for optimistic locks.
        """
        d = self.now()
        i = d.hour * 10000
        i += d.minute * 100
        i += d.second
        return i

    def has_structure(self):
        """ Returns True if the current DB has an animal table """
        try:
            self.execute("select count(*) from animal")
            return True
        except:
            return False

    def insert(self, table, values, user="", generateID=True, setOverrideDBLock=False, setRecordVersion=True, setCreated=True, writeAudit=True):
        """ Inserts a row into a table.
            table: The table to insert into
            values: A dict of column names with values
            user: The user account performing the insert. If set, adds CreatedBy/Date/LastChangedBy/Date fields
            generateID: If True, sets a value for the ID column
            setRecordVersion: If user is non-blank and this is True, sets RecordVersion
            writeAudit: If True, writes an audit record for the insert
            Returns the ID of the inserted record
        """
        if user != "" and setCreated:
            values["CreatedBy"] = user
            values["LastChangedBy"] = user
            values["CreatedDate"] = self.now()
            values["LastChangedDate"] = self.now()
            if setRecordVersion: values["RecordVersion"] = self.get_recordversion()
        iid = 0
        if generateID:
            iid = self.get_id(table)
            values["ID"] = iid
        elif "ID" in values:
            iid = values["ID"]
        values = self.encode_str_before_write(values)
        sql = "INSERT INTO %s (%s) VALUES (%s)" % ( table, ",".join(values.keys()), self.sql_placeholders(values) )
        self.execute(sql, list(values.values()), override_lock=setOverrideDBLock)
        if writeAudit and iid != 0 and user != "":
            asm3.audit.create(self, user, table, iid, asm3.audit.get_parent_links(values, table), asm3.audit.dump_row(self, table, iid))
        return iid

    def update(self, table, where, values, user="", setOverrideDBLock=False, setRecordVersion=True, setLastChanged=True, writeAudit=True):
        """ Updates a row in a table.
            table: The table to update
            where: Either a where clause or an int ID value for ID=where
            values: A dict of column names with values
            user: The user account performing the update. If set, adds CreatedBy/Date/LastChangedBy/Date fields
            setRecordVersion: If user is non-blank and this is True, sets RecordVersion
            writeAudit: If True, writes an audit record for the update
            returns the number of rows updated
        """
        if user != "" and setLastChanged:
            values["LastChangedBy"] = user
            values["LastChangedDate"] = self.now()
            if setRecordVersion: values["RecordVersion"] = self.get_recordversion()
        values = self.encode_str_before_write(values)
        iid = 0
        if asm3.utils.is_numeric(where):
            iid = asm3.utils.cint(where)
            where = "ID=%s" % where
        sql = "UPDATE %s SET %s WHERE %s" % ( table, ",".join( ["%s=?" % x for x in values.keys()] ), where )
        if iid > 0: 
            preaudit = self.query_row(table, iid)
        rows_affected = self.execute(sql, list(values.values()), override_lock=setOverrideDBLock)
        if iid > 0:
            postaudit = self.query_row(table, iid)
        if user != "" and iid > 0 and writeAudit:
            asm3.audit.edit(self, user, table, iid, asm3.audit.get_parent_links(values, table), asm3.audit.map_diff(preaudit, postaudit, asm3.audit.get_readable_fields_for_table(table)))
        return rows_affected

    def delete(self, table, where, user="", writeAudit=True, writeDeletion=True):
        """ Deletes row ID=iid from table 
            table: The table to delete from
            where: Either a where clause or an int ID value for ID=where
            user: The user account doing the delete
            writeAudit: If True, writes an audit record for the delete
            writeDeletion: If True, writes a record to the deletion table
            returns the number of rows deleted
        """
        if asm3.utils.is_numeric(where):
            where = "ID=%s" % asm3.utils.cint(where)
        if writeAudit and user != "":
            asm3.audit.delete_rows(self, user, table, where)
        if writeDeletion and user != "":
            asm3.audit.insert_deletions(self, user, table, where)
        return self.execute("DELETE FROM %s WHERE %s" % (table, where))

    def install_stored_procedures(self):
        """ Install any supporting stored procedures (typically for reports) needed for this backend """
        pass

    def _log_sql(self, sql, params):
        """ If outputting statements to a log is enabled, write the statement
            substitutes any parameters """
        if DB_EXEC_LOG == "":
            return
        if params:
            for p in params:
                sql = sql.replace("%s", self.sql_value(p), 1)
        with open(DB_EXEC_LOG.replace("{database}", self.database), "a") as f:
            f.write("-- %s\n%s;\n" % (self.now(), sql))

    def now(self, timenow=True, offset=0, settime=""):
        """ Returns now as a Python date, adjusted for the database timezone.
            timenow: if True, includes the current time
            offset:  Add this many days to now (negative values supported)
            settime: A time in HH:MM:SS format to set
        """
        tz = self.timezone
        if self.timezone_dst: tz += asm3.i18n.dst_adjust(self.locale, self.timezone)
        d = asm3.i18n.now(tz)
        if not timenow:
            d = d.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
        if offset > 0:
            d = asm3.i18n.add_days(d, offset)
        if offset < 0:
            d = asm3.i18n.subtract_days(d, abs(offset))
        if settime != "":
            timebits = settime.split(":")
            d = d.replace(hour = asm3.utils.cint(timebits[0]), minute = asm3.utils.cint(timebits[1]), second = asm3.utils.cint(timebits[2]), microsecond = 0)
        return d

    def today(self, offset=0, settime=""):
        """ Returns today at midnight
            offset:  Add this many days to now (negative values supported) 
            settime: A time in HH:MM:SS format to set
        """
        return self.now(timenow=False, offset=offset, settime=settime)

    def optimistic_check(self, table, tid, version):
        """ Verifies that the record with ID tid in table still has
        RecordVersion = version.
        If not, returns False otherwise True
        If version is a negative number, that overrides the test and returns true (useful for unit tests
        and any other time we would want to disable optimistic locking)
        """
        if version < 0: return True
        return version == self.query_int("SELECT RecordVersion FROM %s WHERE ID = %d" % (table, tid))

    def query(self, sql, params=None, limit=0, distincton=""):
        """ Runs the query given and returns the resultset as a list of ResultRow objects. 
            All fieldnames are uppercased when returned.
            params: tuple of parameters for the query
            limit: limit results to X rows
            distincton: If set and the field exists, ignores any dups for this field during result construction.
                        This is faster than doing DISTINCT on the full row at the database level
                        (the only thing all RDBMS are guaranteed to support)
        """
        try:
            c, s = self.cursor_open()
            # Add limit clause if set
            if limit > 0:
                sql = "%s %s" % (sql, self.sql_limit(limit))
            # Explain the query if the option is on
            if DB_EXPLAIN_QUERIES:
                esql = "EXPLAIN %s" % sql
                asm3.al.debug(esql, "Database.query", self)
                asm3.al.debug(self.query_explain(esql), "Database.query", self)
            # Record start time
            start = time.time()
            # Run the query and retrieve all rows
            if params:
                sql = self.switch_param_placeholder(sql)
                s.execute(sql, params)
            else:
                s.execute(sql)
            c.commit()
            d = s.fetchall()
            l = []
            cols = []
            # Get the list of column names
            for i in s.description:
                cols.append(i[0].upper())
            seendistinct = set()
            for row in d:
                rowmap = ResultRow()
                for i in range(0, len(row)):
                    v = self.encode_str_after_read(row[i])
                    rowmap[cols[i]] = v
                # If a distinct on value has been set, check for duplicates
                # before adding this row to the resultset
                if distincton != "" and distincton in rowmap:
                    distinctval = rowmap[distincton]
                    if distinctval not in seendistinct:
                        seendistinct.add(distinctval)
                        l.append(rowmap)
                else:
                    l.append(rowmap)
            self.cursor_close(c, s)
            if DB_TIME_QUERIES:
                tt = time.time() - start
                if tt > DB_TIME_LOG_OVER:
                    asm3.al.debug("(%0.2f sec) %s" % (tt, sql), "Database.query", self)
            return l
        except Exception as err:
            asm3.al.error(str(err), "Database.query", self, sys.exc_info())
            asm3.al.error("failing sql: %s %s" % (sql, params), "Database.query", self)
            raise err
        finally:
            try:
                self.cursor_close(c, s)
            except:
                pass

    def query_cache(self, sql, params=None, age=60, limit=0, distincton=""):
        """
        Runs the query given and caches the result
        for age seconds. If there's already a valid cached
        entry for the query, returns the cached result
        instead.
        If CACHE_COMMON_QUERIES is set to false, just runs the query
        without doing any caching and is equivalent to Database.query()
        """
        if not CACHE_COMMON_QUERIES: return self.query(sql, params=params, limit=limit)
        cache_key = "%s:%s:%s" % (self.database, sql, params)
        results = asm3.cachedisk.get(cache_key, self.database, expectedtype=list)
        if results is not None:
            return results
        results = self.query(sql, params=params, limit=limit, distincton=distincton)
        asm3.cachedisk.put(cache_key, self.database, results, age)
        return results

    def query_columns(self, sql, params=None):
        """
            Runs the query given and returns the column names as
            a list in the order they appeared in the query
        """
        try:
            c, s = self.cursor_open()
            # Run the query and retrieve all rows
            if params:
                sql = self.switch_param_placeholder(sql)
                s.execute(sql, params)
            else:
                s.execute(sql)
            c.commit()
            # Build a list of the column names
            cn = []
            for col in s.description:
                cn.append(col[0].upper())
            self.cursor_close(c, s)
            return cn
        except Exception as err:
            asm3.al.error(str(err), "Database.query_columns", self, sys.exc_info())
            asm3.al.error("failing sql: %s %s" % (sql, params), "Database.query_columns", self)
            raise err
        finally:
            try:
                self.cursor_close(c, s)
            except:
                pass

    def query_explain(self, sql, params=None):
        """
        Runs an EXPLAIN query
        """
        if not sql.lower().startswith("EXPLAIN "):
            sql = "EXPLAIN %s" % sql
        rows = self.query_tuple(sql, params=params)
        o = []
        for r in rows:
            o.append(r[0])
        return "\n".join(o)

    def query_generator(self, sql, params=None):
        """ Runs the query given and returns the resultset as a list of dictionaries. 
            All fieldnames are uppercased when returned. 
            generator function version that uses a forward cursor.
        """
        try:
            c, s = self.cursor_open()
            # Run the query and retrieve all rows
            if params:
                sql = self.switch_param_placeholder(sql)
                s.execute(sql, params)
            else:
                s.execute(sql)
            c.commit()
            cols = []
            # Get the list of column names
            for i in s.description:
                cols.append(i[0].upper())
            row = s.fetchone()
            while row:
                # Intialise a map for each row
                rowmap = {}
                for i in range(0, len(row)):
                    v = self.encode_str_after_read(row[i])
                    rowmap[cols[i]] = v
                yield rowmap
                row = s.fetchone()
            self.cursor_close(c, s)
        except Exception as err:
            asm3.al.error(str(err), "Database.query_generator", self, sys.exc_info())
            asm3.al.error("failing sql: %s %s" % (sql, params), "Database.query_generator", self)
            raise err
        finally:
            try:
                self.cursor_close(c, s)
            except:
                pass

    def query_named_params(self, sql, params, age=0):
        """ Allows use of :named :params in a query (must terminate with space, comma or right parentheses). params should be a dict. 
            if age is not zero, uses query_cache instead.
        """
        def lowest(*args):
            r = 99999
            for z in args:
                if z != -1 and z < r:
                    r = z
            return r
        x = 0
        values = []
        while True:
            if sql[x:x+1] == ":":
                # Use the next space, comma or ) as separator
                y = lowest(sql.find(" ", x), sql.find(",", x), sql.find(")", x))
                pname = sql[x+1:y]
                sql = sql[0:x] + "?" + sql[y:]
                values.append(params[pname])
                x = y
            x += 1
            if x >= len(sql): break
        if age == 0:
            return self.query(sql, values)
        else:
            return self.query_cache(sql, values, age=age)

    def query_row(self, table, iid):
        """ Returns the complete table row with ID=iid """
        return self.query("SELECT * FROM %s WHERE ID=%s" % (table, iid))

    def query_to_insert_sql(self, sql, table, escapeCR = ""):
        """
        Generator function that Writes an INSERT query for the list of rows 
        returned by running sql (a list containing dictionaries)
        escapeCR: Turn line feed chars into this character
        """
        for r in self.query_generator(sql):
            yield self.row_to_insert_sql(table, r, escapeCR)

    def query_tuple(self, sql, params=None, limit=0):
        """ Runs the query given and returns the resultset
            as a tuple of tuples.
        """
        try:
            c, s = self.cursor_open()
            # Add limit clause if set
            if limit > 0:
                sql = "%s %s" % (sql, self.sql_limit(limit))
            # Run the query and retrieve all rows
            if params:
                sql = self.switch_param_placeholder(sql)
                s.execute(sql, params)
            else:
                s.execute(sql)
            d = s.fetchall()
            c.commit()
            self.cursor_close(c, s)
            return d
        except Exception as err:
            asm3.al.error(str(err), "Database.query_tuple", self, sys.exc_info())
            asm3.al.error("failing sql: %s %s" % (sql, params), "Database.query_tuple", self)
            raise err
        finally:
            try:
                self.cursor_close(c, s)
            except:
                pass

    def query_tuple_columns(self, sql, params=None, limit=0):
        """ Runs the query given and returns the resultset
            as a grid of tuples and a list of columnames
        """
        try:
            c, s = self.cursor_open()
            # Add limit clause if set
            if limit > 0:
                sql = "%s %s" % (sql, self.sql_limit(limit))
            # Run the query and retrieve all rows
            if params: 
                sql = self.switch_param_placeholder(sql)
                s.execute(sql, params)
            else:
                s.execute(sql)
            d = s.fetchall()
            c.commit()
            # Build a list of the column names
            cn = []
            for col in s.description:
                cn.append(col[0].upper())
            self.cursor_close(c, s)
            return (d, cn)
        except Exception as err:
            asm3.al.error(str(err), "Database.query_tuple_columns", self, sys.exc_info())
            asm3.al.error("failing sql: %s %s" % (sql, params), "Database.query_tuple_columns", self)
            raise err
        finally:
            try:
                self.cursor_close(c, s)
            except:
                pass

    def query_int(self, sql, params=None):
        """ Runs a query and returns the first item from the first column as an integer """
        r = self.query_tuple(sql, params=params)
        try:
            v = r[0][0]
            return int(v)
        except:
            return int(0)

    def query_float(self, sql, params=None):
        """ Runs a query and returns the first item from the first column as a float """
        r = self.query_tuple(sql, params=params)
        try:
            v = r[0][0]
            return float(v)
        except:
            return float(0)

    def query_string(self, sql, params=None):
        """ Runs a query and returns the first item from the first column as a string """
        r = self.query_tuple(sql, params=params)
        try:
            if r[0][0] is None: return ""
            return str(self.encode_str_after_read(r[0][0]))
        except:
            return ""

    def query_date(self, sql, params=None):
        """ Runs a query and returns the first item from the first column as a date """
        r = self.query_tuple(sql, params=params)
        try:
            v = r[0][0]
            return v
        except:
            return None

    def row_to_insert_sql(self, table, r, escapeCR = ""):
        """
        function that Writes an INSERT query for a result row
        """
        fields = []
        donefields = False
        values = []
        for k in sorted(r.keys()):
            if not donefields:
                fields.append(k)
            values.append(self.sql_value(r[k]))
        donefields = True
        return "INSERT INTO %s (%s) VALUES (%s);\n" % (table, ",".join(fields), ",".join(values))

    def split_queries(self, sql):
        """
        Splits semi-colon separated queries in a single
        string into a list and returns them for execution.
        """
        queries = []
        x = 0
        instr = False
        while x <= len(sql):
            q = sql[x:x+1]
            if q == "'":
                instr = not instr
            if x == len(sql):
                queries.append(sql[0:x].strip())
                break
            if q == ";" and not instr:
                queries.append(sql[0:x].strip())
                sql = sql[x+1:]
                x = 0
                continue
            x += 1
        return queries

    def sql_atoi(self, fieldexpr):
        """ Removes all but the numbers from fieldexpr """
        return self.sql_regexp_replace(fieldexpr, r"[^0123456789]", "")

    def sql_cast(self, expr, newtype):
        """ Writes a database independent cast for expr to newtype """
        return "CAST(%s AS %s)" % (expr, newtype)

    def sql_cast_char(self, expr):
        """ Writes a database independent cast for expr to a char """
        return self.sql_cast(expr, "TEXT")

    def sql_char_length(self, item):
        """ Writes a database independent char length """
        return "LENGTH(%s)" % item

    def sql_concat(self, items):
        """ Writes concat for a list of items """
        return " || ".join(items)

    def sql_date(self, d, wrapParens=True, includeTime=True):
        """ Writes a Python date in SQL form """
        if d is None: return "NULL"
        s = "%04d-%02d-%02d %02d:%02d:%02d" % ( d.year, d.month, d.day, d.hour, d.minute, d.second )
        if not includeTime:
            s = "%04d-%02d-%02d" % ( d.year, d.month, d.day )
        if wrapParens: return "'%s'" % s
        return s

    def sql_greatest(self, items):
        """ Writes greatest for a list of items """
        return "GREATEST(%s)" % ",".join(items)

    def sql_ilike(self, expr1, expr2 = "?"):
        """ Writes the SQL for an insensitive like comparison, 
            eg: sql_ilike("field", "?")    ==     LOWER(field) LIKE ? 
            requires expr2 to be lower case if it is a string literal.
        """
        return f"LOWER({expr1}) LIKE {expr2}"

    def sql_placeholders(self, l):
        """ Writes enough ? placeholders for items in l """
        return ",".join('?'*len(l))

    def sql_now(self, wrapParens=True, includeTime=True):
        """ Writes now as an SQL date """
        return self.sql_date(self.now(), wrapParens=wrapParens, includeTime=includeTime)

    def sql_limit(self, x):
        """ Writes a limit clause to X items """
        return "LIMIT %s" % x

    def sql_regexp_replace(self, fieldexpr, pattern="?", replacestr="?"):
        """ Writes a regexp replace expression that replaces characters matching pattern with replacestr """
        if pattern != "?": pattern = "'%s'" % pattern
        if replacestr != "?": replacestr = "'%s'" % self.escape(replacestr)
        return "REGEXP_REPLACE(%s, %s, %s)" % (fieldexpr, pattern, replacestr)

    def sql_replace(self, fieldexpr, findstr="?", replacestr="?"):
        """ Writes a replace expression that finds findstr in fieldexpr, replacing with replacestr """
        if findstr != "?": findstr = "'%s'" % self.escape(findstr)
        if replacestr != "?": replacestr = "'%s'" % self.escape(replacestr)
        return "REPLACE(%s, %s, %s)" % (fieldexpr, findstr, replacestr)

    def sql_substring(self, fieldexpr, pos, chars):
        """ SQL substring function from pos for chars """
        return "SUBSTR(%s, %s, %s)" % (fieldexpr, pos, chars)

    def sql_today(self, wrapParens=True, includeTime=True):
        """ Writes today as an SQL date """
        return self.sql_date(self.today(), wrapParens=wrapParens, includeTime=includeTime)

    def sql_value(self, v):
        """ Given a value v, writes it as an SQL parameter value """
        if v is None:
            return "null"
        elif asm3.utils.is_unicode(v) or asm3.utils.is_str(v):
            return "'%s'" % v.replace("'", "''")
        elif type(v) == datetime.datetime:
            return self.sql_date(v)
        else:
            return str(v)

    def sql_zero_pad_left(self, fieldexpr, digits):
        """ Writes a function that zero pads an expression with zeroes to digits """
        return fieldexpr

    def stats(self):
        return self.first_row(self.query("select " \
            "(select count(*) from animal where archived=0) as shelteranimals, " \
            "(select count(*) from animal) as totalanimals, " \
            "(select min(createddate) from animal) as firstrecord, " \
            "(select count(*) from owner) as totalpeople, " \
            "(select count(*) from adoption) as totalmovements, " \
            "(select count(*) from media) as totalmedia, " \
            "(select sum(mediasize) / 1024.0 / 1024.0 from media) as mediasize, " \
            "(select count(*) from media where mediamimetype='image/jpeg') as totaljpg, " \
            "(select sum(mediasize) / 1024.0 / 1024.0 from media where mediamimetype='image/jpeg') as jpgsize, " \
            "(select count(*) from media where mediamimetype='application/pdf') as totalpdf, " \
            "(select sum(mediasize) / 1024.0 / 1024.0 from media where mediamimetype='application/pdf') as pdfsize "))

    def switch_param_placeholder(self, sql):
        """ Swaps the ? token in the sql for the usual Python DBAPI placeholder of %s 
            override if your DB driver wants another char.
        """
        return sql.replace("?", "%s")

    def update_asm2_primarykey(self, table, nextid):
        """
        Update the ASM2 primary key table.
        """
        if not self.has_asm2_pk_table: return
        try:
            self.execute("DELETE FROM primarykey WHERE TableName = ?", [table] )
            self.execute("INSERT INTO primarykey (TableName, NextID) VALUES (?, ?)", (table, nextid))
        except:
            pass

    def __repr__(self):
        return "Database->locale=%s:dbtype=%s:host=%s:port=%d:db=%s:user=%s:timeout=%s" % ( self.locale, self.dbtype, self.host, self.port, self.database, self.username, self.timeout )


