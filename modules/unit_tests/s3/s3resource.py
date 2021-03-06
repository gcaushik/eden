# -*- coding: utf-8 -*-
#
# S3Resource Unit Tests
#
# To run this script use:
# python web2py.py -S eden -M -R applications/eden/modules/unit_tests/s3/s3resource.py
#
import unittest
import datetime
from lxml import etree
from gluon import *
from gluon.storage import Storage
from gluon.dal import Row
from s3.s3resource import *
from s3.s3fields import s3_meta_fields

# =============================================================================
class ComponentJoinConstructionTests(unittest.TestCase):
    """ Test component join construction """

    # -------------------------------------------------------------------------
    def testGetJoinMaster(self):
        """ Master resource has no join """

        resource = current.s3db.resource("pr_person")
        
        self.assertEqual(resource.get_join(), None)

    # -------------------------------------------------------------------------
    def testGetJoinSimpleComponent(self):
        """ Join for a simple component """

        resource = current.s3db.resource("pr_person")
        component = resource.components["identity"]

        rtable = resource.table
        ctable = component.table
        expected = (ctable.person_id == rtable.id) & \
                   (ctable.deleted != True)
                   
        join = component.get_join()
        self.assertEqual(str(join), str(expected))

    # -------------------------------------------------------------------------
    def testGetJoinSuperComponent(self):
        """ Join for a super-component """

        resource = current.s3db.resource("pr_person")
        component = resource.components["contact"]
        
        rtable = resource.table
        ctable = component.table
        expected = (rtable.pe_id == ctable.pe_id) & \
                   (ctable.deleted != True)
                   
        join = component.get_join()
        self.assertEqual(str(join), str(expected))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testGetJoinLinkTableComponent(self):
        """ Join for a link-table component """

        resource = current.s3db.resource("project_project")
        component = resource.components["task"]
        
        rtable = resource.table
        ltable = component.link.table
        ctable = component.table
        expected = (ltable.deleted != True) & \
                   ((ltable.project_id == rtable.id) & \
                    (ltable.task_id == ctable.id))

        join = component.get_join()
        self.assertEqual(str(join), str(expected))

# =============================================================================
class ComponentLeftJoinConstructionTests(unittest.TestCase):
    """ Test component left join construction """

    # -------------------------------------------------------------------------
    def testGetLeftJoinMaster(self):
        """ Master resource has no left join """

        resource = current.s3db.resource("pr_person")
        self.assertEqual(resource.get_left_join(), None)

    # -------------------------------------------------------------------------
    def testGetLeftJoinSimpleComponent(self):
        """ Left Join for a simple component """

        resource = current.s3db.resource("pr_person")
        component = resource.components["identity"]

        rtable = resource.table
        ctable = component.table
        expected = ctable.on((ctable.person_id == rtable.id) &
                             (ctable.deleted != True))

        ljoin = component.get_left_join()
        self.assertTrue(isinstance(ljoin, list))
        self.assertEqual(len(ljoin), 1)
        self.assertEqual(str(ljoin[0]), str(expected))

    # -------------------------------------------------------------------------
    def testGetLeftJoinSuperComponent(self):
        """ Left Join for a super-component """

        resource = current.s3db.resource("pr_person")
        component = resource.components["contact"]
        
        rtable = resource.table
        ctable = component.table
        expected = ctable.on((rtable.pe_id == ctable.pe_id) &
                             (ctable.deleted != True))

        ljoin = component.get_left_join()
        self.assertTrue(isinstance(ljoin, list))
        self.assertEqual(len(ljoin), 1)
        self.assertEqual(str(ljoin[0]), str(expected))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testGetLeftJoinLinkTableComponent(self):
        """ Left Join for a link-table component """

        resource = current.s3db.resource("project_project")
        component = resource.components["task"]
        
        rtable = resource.table
        ltable = component.link.table
        ctable = component.table
        
        expected_l = ltable.on((ltable.project_id == rtable.id) &
                               (ltable.deleted != True))
        expected_r = ctable.on(ltable.task_id == ctable.id)

        ljoin = component.get_left_join()
        self.assertTrue(isinstance(ljoin, list))
        self.assertEqual(len(ljoin), 2)
        self.assertEqual(str(ljoin[0]), str(expected_l))
        self.assertEqual(str(ljoin[1]), str(expected_r))

# =============================================================================
class FieldSelectorResolutionTests(unittest.TestCase):
    """ Test field selector resolution """

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testResolveSelectorsWithoutComponents(self):
        """ Field selector resolution without components"""

        s3db = current.s3db
        
        resource = s3db.resource("project_project")
        selectors = ["id",
                     "name",
                     "organisation_id$name",
                     "task.description"]
        fields, joins, left, distinct = resource.resolve_selectors(selectors,
                                                                   skip_components=True)
                                                                   
        project_project = resource.table
        org_organisation = s3db.org_organisation

        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)

        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0].colname, "project_project.id")
        self.assertEqual(fields[1].colname, "project_project.name")
        self.assertEqual(fields[2].colname, "org_organisation.name")
        
        self.assertEqual(joins, Storage())
        
        self.assertTrue(isinstance(left, Storage))
        self.assertEqual(left.keys(), ["org_organisation"])
        self.assertEqual(len(left["org_organisation"]), 1)
        self.assertEqual(str(left["org_organisation"][0]), str(expected))
        
        self.assertTrue(distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testResolveSelectorsWithComponents(self):
        """ Field selector resolution with components"""

        s3db = current.s3db

        resource = s3db.resource("project_project")
        selectors = ["id",
                     "name",
                     "organisation_id$name",
                     "task.description"]
        fields, joins, left, distinct = resource.resolve_selectors(selectors)

        project_project = resource.table
        org_organisation = s3db.org_organisation
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)

        expected_l = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))

        expected_r = project_task.on(
                        project_task_project.task_id == project_task.id)

        self.assertEqual(len(fields), 4)
        self.assertEqual(fields[0].colname, "project_project.id")
        self.assertEqual(fields[1].colname, "project_project.name")
        self.assertEqual(fields[2].colname, "org_organisation.name")
        self.assertEqual(fields[3].colname, "project_task.description")
        
        self.assertEqual(joins, Storage())
        
        self.assertTrue(isinstance(left, Storage))
        self.assertEqual(left.keys(), [ "org_organisation", "project_task"])
        self.assertEqual(len(left["org_organisation"]), 1)
        self.assertEqual(str(left["org_organisation"][0]), str(expected))
        self.assertEqual(len(left["project_task"]), 2)
        self.assertEqual(str(left["project_task"][0]), str(expected_l))
        self.assertEqual(str(left["project_task"][1]), str(expected_r))
        
        self.assertTrue(distinct)

# =============================================================================
class ResourceFilterJoinTests(unittest.TestCase):
    """ Test query construction from S3ResourceQueries """

    # -------------------------------------------------------------------------
    def setUp(self):

        current.auth.override = True

    # -------------------------------------------------------------------------
    def testGetQueryJoinsInnerField(self):
        """ Inner field queries don't contain joins """

        resource = current.s3db.resource("pr_person")
        q = S3FieldSelector("first_name") == "test"

        # Test joins
        joins, distinct = q.joins(resource)
        self.assertEqual(joins, Storage())
        self.assertFalse(distinct)

        # Test left joins
        joins, distinct = q.joins(resource, left=True)
        self.assertEqual(joins, Storage())
        self.assertFalse(distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testGetQueryJoinsReferencedTableField(self):
        """ Referenced table field queries use left joins + distinct """

        s3db = current.s3db

        resource = s3db.resource("project_project")
        q = S3FieldSelector("organisation_id$name") == "test"

        # Test joins
        joins, distinct = q.joins(resource)
        self.assertEqual(joins, Storage())
        self.assertTrue(distinct)

        # Test left joins
        project_project = resource.table
        org_organisation = s3db.org_organisation
        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)
        
        joins, distinct = q.joins(resource, left=True)
        self.assertTrue(isinstance(joins, Storage))
        self.assertEqual(joins.keys(), ["org_organisation"])
        self.assertTrue(isinstance(joins["org_organisation"], list))
        self.assertEqual(len(joins["org_organisation"]), 1)
        self.assertEqual(str(joins["org_organisation"][0]), str(expected))
        self.assertTrue(distinct)

    # -------------------------------------------------------------------------
    def testGetQueryJoinsComponentField(self):
        """ Component field queries use left joins + distinct """

        s3db = current.s3db

        resource = s3db.resource("pr_person")
        q = S3FieldSelector("identity.value") == "test"

        # Test joins
        joins, distinct = q.joins(resource)
        self.assertEqual(joins, Storage())
        self.assertTrue(distinct)

        pr_person = resource.table
        pr_identity = s3db.pr_identity
        expected = pr_identity.on(
                        (pr_identity.person_id == pr_person.id) &
                        (pr_identity.deleted != True))

        # Test left joins
        joins, distinct = q.joins(resource, left=True)
        self.assertEqual(joins.keys(), ["pr_identity"])
        self.assertTrue(isinstance(joins["pr_identity"], list))
        self.assertEqual(str(joins["pr_identity"][0]), str(expected))
        self.assertTrue(distinct)

    # -------------------------------------------------------------------------
    def testGetQueryJoinsSuperComponentField(self):
        """ Super component field queries use left joins + distinct """

        s3db = current.s3db
        
        resource = s3db.resource("pr_person")
        q = S3FieldSelector("contact.value") == "test"

        # Test joins
        joins, distinct = q.joins(resource)
        self.assertEqual(joins, Storage())
        self.assertTrue(distinct)

        # Test left joins
        pr_person = resource.table
        pr_contact = s3db.pr_contact
        expected = pr_contact.on(
                        (pr_person.pe_id == pr_contact.pe_id) &
                        (pr_contact.deleted != True))

        joins, distinct = q.joins(resource, left=True)
        self.assertEqual(joins.keys(), ["pr_contact"])
        self.assertTrue(isinstance(joins["pr_contact"], list))
        self.assertEqual(str(joins["pr_contact"][0]), str(expected))
        self.assertTrue(distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testGetQueryJoinsLinkedComponentField(self):
        """
            Link table component field queries use chained left
            joins + distinct
        """

        s3db = current.s3db

        resource = s3db.resource("project_project")
        q = S3FieldSelector("task.description") == "test"

        # Test joins
        joins, distinct = q.joins(resource)
        self.assertEqual(joins, Storage())
        self.assertTrue(distinct)

        # Test left joins
        project_project = resource.table
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        expected_l = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))

        expected_r = project_task.on(
                        project_task_project.task_id == project_task.id)

        joins, distinct = q.joins(resource, left=True)
        self.assertEqual(joins.keys(), ["project_task"])
        self.assertTrue(isinstance(joins["project_task"], list))
        self.assertEqual(len(joins["project_task"]), 2)
        self.assertEqual(str(joins["project_task"][0]), str(expected_l))
        self.assertEqual(str(joins["project_task"][1]), str(expected_r))
        self.assertTrue(distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testGetQueryJoinsCombination(self):
        """ Queries for fields in multiple tables use multiple joins """

        s3db = current.s3db

        resource = s3db.resource("project_project")
        q = (S3FieldSelector("organisation_id$name") == "test") & \
            (S3FieldSelector("task.description") == "test")

        # Test joins
        joins, distinct = q.joins(resource)
        self.assertEqual(joins.keys(), [])

        # Test left joins
        project_project = resource.table
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task
        org_organisation = s3db.org_organisation
        
        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)

        expected_l = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))

        expected_r = project_task.on(
                        project_task_project.task_id == project_task.id)

        joins, distinct = q.joins(resource, left=True)
        self.assertEqual(joins.keys(), ["org_organisation", "project_task"])

        self.assertTrue(isinstance(joins["org_organisation"], list))
        self.assertEqual(len(joins["org_organisation"]), 1)
        self.assertEqual(str(joins["org_organisation"][0]), str(expected))
        self.assertTrue(isinstance(joins["project_task"], list))
        self.assertEqual(len(joins["project_task"]), 2)
        self.assertEqual(str(joins["project_task"][0]), str(expected_l))
        self.assertEqual(str(joins["project_task"][1]), str(expected_r))
        self.assertTrue(distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testGetFilterLeftJoins(self):
        """ Check list of left joins in resource filters """

        s3db = current.s3db

        q = (S3FieldSelector("organisation_id$name") == "test") & \
            (S3FieldSelector("task.description") == "test")
        resource = s3db.resource("project_project", filter=q)

        # Test left joins
        project_project = resource.table
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task
        org_organisation = s3db.org_organisation
        
        expected1 = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)

        expected2 = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))

        expected3 = project_task.on(project_task_project.task_id == project_task.id)
        
        joins = resource.rfilter.get_left_joins()
        self.assertTrue(isinstance(joins, list))
        self.assertEqual(len(joins), 3)

        self.assertEqual(str(joins[0]), str(expected1))
        self.assertEqual(str(joins[1]), str(expected2))
        self.assertEqual(str(joins[2]), str(expected3))

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.auth.override = False

# =============================================================================
class ResourceFilterQueryTests(unittest.TestCase):
    """ Test resource filter query construction """

    # -------------------------------------------------------------------------
    def setUp(self):

        current.auth.override = True

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testTextOperatorWithNonTextField(self):
        """ Test query construction for non-text fields with text operator """

        s3db = current.s3db

        q = (S3FieldSelector("id").lower().like("%123%"))
        resource = s3db.resource("org_organisation", filter=q)
        query = resource.rfilter.get_query()
        org_organisation = resource.table
        expected = (((org_organisation.deleted != True) &
                     (org_organisation.id > 0)) &
                    (org_organisation.id.like("%123%")))
        self.assertEqual(str(query), str(expected))

        q = (S3FieldSelector("id").lower().like("%12%3%"))
        resource = s3db.resource("org_organisation", filter=q)
        query = resource.rfilter.get_query()
        org_organisation = resource.table
        expected = (((org_organisation.deleted != True) &
                     (org_organisation.id > 0)) &
                    (org_organisation.id.like("%12%3%")))
        self.assertEqual(str(query), str(expected))

        q = (S3FieldSelector("id").lower().like("%abc%"))
        resource = s3db.resource("org_organisation", filter=q)
        query = resource.rfilter.get_query()
        org_organisation = resource.table
        expected = (((org_organisation.deleted != True) &
                     (org_organisation.id > 0)) &
                    (org_organisation.id.like("%abc%")))
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testMasterFilterConstruction(self):
        """ Test master resource filter construction """

        s3db = current.s3db

        project_project = s3db.project_project
        org_organisation = s3db.org_organisation
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        q = (S3FieldSelector("organisation_id$name") == "test") & \
            (S3FieldSelector("task.description") == "test")
        resource = current.s3db.resource("project_project", filter=q)

        rfilter = resource.rfilter
        self.assertNotEqual(rfilter, None)

        # Check master query
        expected = ((project_project.deleted != True) &
                    (project_project.id > 0))
        self.assertEqual(str(rfilter.mquery), str(expected))

        # Check effective query
        expected = (((project_project.deleted != True) &
                     (project_project.id > 0)) &
                     ((org_organisation.name == "test") &
                      (project_task.description == "test")))
        query = rfilter.get_query()
        self.assertEqual(str(query), str(expected))

        # Check joins
        joins = rfilter.joins
        self.assertEqual(joins.keys(), [])

        # Check left joins
        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)

        expected_l = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))

        expected_r = project_task.on(
                        project_task_project.task_id == project_task.id)

        left = rfilter.get_left_joins(as_list=False)
        self.assertEqual(left.keys(), ["org_organisation", "project_task"])
        self.assertTrue(isinstance(left["org_organisation"], list))
        self.assertEqual(len(left["org_organisation"]), 1)
        self.assertEqual(str(left["org_organisation"][0]), str(expected))
        self.assertTrue(isinstance(left["project_task"], list))
        self.assertEqual(len(left["project_task"]), 2)
        self.assertEqual(str(left["project_task"][0]), str(expected_l))
        self.assertEqual(str(left["project_task"][1]), str(expected_r))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testCrossComponentFilterConstruction1(self):
        """ Test cross-component effect of master resource filter """

        s3db = current.s3db

        project_project = s3db.project_project
        org_organisation = s3db.org_organisation
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        q1 = (S3FieldSelector("organisation_id$name") == "test")
        q2 = (S3FieldSelector("task.description") == "test")
        resource = s3db.resource("project_project", filter=q1)
        resource.add_filter(q2)

        component = resource.components["task"]
        component.build_query()
        rfilter = component.rfilter
        query = rfilter.get_query()

        expected = ((((project_task.deleted != True) &
                   (project_task.id > 0)) &
                   (((project_project.deleted != True) &
                   (project_project.id > 0)) &
                   ((org_organisation.name == "test") &
                   (project_task.description == "test")))) &
                   ((project_task_project.deleted != True) &
                   ((project_task_project.project_id == project_project.id) &
                   (project_task_project.task_id == project_task.id))))
                    
        self.assertEqual(query, expected)
        
        left = rfilter.get_left_joins(as_list=False)
        tablenames = left.keys()
        self.assertEqual(len(tablenames), 2)
        self.assertTrue("org_organisation" in tablenames)
        self.assertTrue("project_project" in tablenames)
        
        self.assertTrue(isinstance(left["org_organisation"], list))
        self.assertEqual(len(left["org_organisation"]), 1)
        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)
        self.assertEqual(str(left["org_organisation"][0]), str(expected))
        
        self.assertTrue(isinstance(left["project_project"], list))
        self.assertEqual(len(left["project_project"]), 2)
        expected = project_task_project.on(project_task_project.task_id == project_task.id)
        self.assertEqual(str(left["project_project"][0]), str(expected))
        expected = project_project.on((project_task_project.project_id == project_project.id) &
                                      (project_task_project.deleted != True))
        self.assertEqual(str(left["project_project"][1]), str(expected))

        # Try to select rows
        rows = component.select(None, limit=1, as_rows=True)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("hrm"), "hrm module disabled")
    def testCrossComponentFilterConstruction2(self):
        """ Test cross-component effect of master resource filter """

        s3db = current.s3db

        pr_identity = s3db.pr_identity
        pr_person = s3db.pr_person
        org_organisation = s3db.org_organisation
        hrm_human_resource = s3db.hrm_human_resource

        q1 = (S3FieldSelector("human_resource.organisation_id$name") == "test")
        q2 = (S3FieldSelector("identity.value") == "test")
        resource = s3db.resource("pr_person", filter=q1)

        resource.add_filter(q2)

        component = resource.components["identity"]
        component.build_query()
        rfilter = component.rfilter
        query = rfilter.get_query()
                    
        expected = ((((pr_identity.deleted != True) &
                   (pr_identity.id > 0)) &
                   (((pr_person.deleted != True) &
                   (pr_person.id > 0)) &
                   ((org_organisation.name == "test") &
                   (pr_identity.value == "test")))) &
                   ((pr_identity.person_id == pr_person.id) &
                   (pr_identity.deleted != True))) # Duplicated!
                   
        self.assertEqual(query, expected)
        
        # Check left joins
        expected_h = hrm_human_resource.on(
                        (hrm_human_resource.person_id == pr_person.id) &
                        (hrm_human_resource.deleted != True))
        expected_o = org_organisation.on(
                        hrm_human_resource.organisation_id == org_organisation.id)
        expected_p = pr_person.on(pr_identity.person_id == pr_person.id)

        left = rfilter.get_left_joins(as_list=False)
        tablenames = left.keys()
        self.assertEqual(len(tablenames), 3)
        self.assertTrue("hrm_human_resource" in tablenames)
        self.assertTrue("org_organisation" in tablenames)
        self.assertTrue("pr_person" in tablenames)
        
        self.assertTrue(isinstance(left["hrm_human_resource"], list))
        self.assertEqual(len(left["hrm_human_resource"]), 1)
        self.assertEqual(str(left["hrm_human_resource"][0]), str(expected_h))
        self.assertTrue(isinstance(left["org_organisation"], list))
        self.assertEqual(len(left["org_organisation"]), 1)
        self.assertEqual(str(left["org_organisation"][0]), str(expected_o))
        self.assertEqual(len(left["pr_person"]), 1)
        self.assertEqual(str(left["pr_person"][0]), str(expected_p))
        
        # Try to select rows
        rows = component.select(None, limit=1, as_rows=True)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testSimpleComponentFilterConstruction1(self):
        """ Test simple component filter construction (check query in filter) """

        s3db = current.s3db

        project_project = s3db.project_project
        project_activity = s3db.project_activity

        resource = s3db.resource("project_project", id=1)

        component = resource.components["activity"]
        component.build_query()
        rfilter = component.rfilter
        query = rfilter.get_query()

        # This will fail in 1st run as there is no ADMIN role yet

        expected = ((((project_activity.deleted != True) &
                      (project_activity.id > 0)) &
                     (((project_project.deleted != True) &
                       (project_project.id > 0)) &
                      (project_project.id == 1))) &
                    ((project_activity.project_id == project_project.id) &
                     (project_activity.deleted != True)))
        
        self.assertEqual(str(query), str(expected))
        self.assertEqual(rfilter.get_left_joins(as_list=False), Storage())
        
        # Try to select rows
        rows = component.select(None, limit=1, as_rows=True)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("hrm"), "hrm module disabled")
    def testSimpleComponentFilterConstruction2(self):
        """ Test simple component filter construction (check query in resource) """

        s3db = current.s3db

        pr_person = s3db.pr_person
        hrm_competency = s3db.hrm_competency

        resource = current.s3db.resource("pr_person",
                                         id=1,
                                         components=["competency"],
                                         filter=(S3FieldSelector("competency.id") == 1))

        component = resource.components["competency"]
        query = component.get_query()

        expected = ((((hrm_competency.deleted != True) &
                      (hrm_competency.id > 0)) &
                     ((((pr_person.deleted != True) &
                        (pr_person.id > 0)) &
                       (pr_person.id == 1)) &
                     (hrm_competency.id == 1))) &
                    ((hrm_competency.person_id == pr_person.id) &
                     (hrm_competency.deleted != True)))
                     
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    def testAnyOf(self):
        """ Test filter construction with containment methods (contains vs anyof) """

        FS = S3FieldSelector

        resource = current.s3db.resource("req_req_skill")
        req_req_skill = resource.table
        
        q = FS("skill_id").contains([1, 2])
        query = q.query(resource)
        expected = ((req_req_skill.skill_id.like("%|1|%")) &
                    (req_req_skill.skill_id.like("%|2|%")))
        self.assertEqual(str(query), str(expected))
        
        q = FS("skill_id").anyof([1, 2])
        query = q.query(resource)
        expected = ((req_req_skill.skill_id.like("%|1|%")) |
                    (req_req_skill.skill_id.like("%|2|%")))
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.auth.override = False

# =============================================================================
class ResourceContextFilterTests(unittest.TestCase):
    """ Test global context filter """

    def setUp(self):

        # Two organisations with offices and human resources,
        # one person record linked to both organisation contexts
        xmlstr = """
<s3xml>
    <resource name="org_organisation" uuid="CONTEXTORG1">
        <data field="name">ContextFilterTestOrg1</data>
        <resource name="org_office" uuid="CONTEXT1OFFICE1">
            <data field="name">Context1Office1</data>
        </resource>
        <resource name="org_office" uuid="CONTEXT1OFFICE2">
            <data field="name">Context1Office2</data>
        </resource>
        <resource name="hrm_human_resource" uuid="CONTEXT1HR1">
            <reference field="person_id" resource="pr_person">
                <resource name="pr_person" uuid="CONTEXT1PERSON">
                    <data field="first_name">Context1</data>
                    <data field="last_name">Person</data>
                </resource>
            </reference>
        </resource>
        <resource name="hrm_human_resource" uuid="CONTEXT1HR2">
            <reference field="person_id" resource="pr_person">
                <resource name="pr_person" uuid="CONTEXT12PERSON">
                    <data field="first_name">Context12</data>
                    <data field="last_name">Person</data>
                </resource>
            </reference>
        </resource>
    </resource>
    <resource name="org_organisation" uuid="CONTEXTORG2">
        <data field="name">ContextFilterTestOrg2</data>
        <resource name="org_office" uuid="CONTEXT2OFFICE1">
            <data field="name">Context2Office1</data>
        </resource>
        <resource name="hrm_human_resource" uuid="CONTEXT2HR1">
            <reference field="person_id" resource="pr_person">
                <resource name="pr_person" uuid="CONTEXT2PERSON">
                    <data field="first_name">Context2</data>
                    <data field="last_name">Person</data>
                </resource>
            </reference>
        </resource>
        <resource name="hrm_human_resource" uuid="CONTEXT2HR2">
            <reference field="person_id" resource="pr_person" uuid="CONTEXT12PERSON"/>
        </resource>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))

        current.auth.override = True
        resource = current.s3db.resource("org_organisation")
        resource.import_xml(xmltree)
        
    # -------------------------------------------------------------------------
    def testContextFilter(self):
        """ Test global context filter """
        
        s3db = current.s3db

        # Configure contexts
        s3db.configure("org_office",
                       context = {"organisation":
                                  "organisation_id"})
        s3db.configure("pr_person",
                       context = {"organisation":
                                  "human_resource.organisation_id"})
                                    
        # Without global context filter
        s3db.context = None
                                    
        resource = s3db.resource("org_office",
                                 uid=["CONTEXT1OFFICE1",
                                      "CONTEXT1OFFICE2",
                                      "CONTEXT2OFFICE1"],
                                 context=True)
        data = resource.select(["name"], limit=None)
        items = data["rows"]
        self.assertEqual(len(items), 3)
        names = [item.values()[0] for item in items]
        self.assertTrue("Context1Office1" in names)
        self.assertTrue("Context1Office2" in names)
        self.assertTrue("Context2Office1" in names)

        resource = s3db.resource("pr_person",
                                 uid=["CONTEXT1PERSON",
                                      "CONTEXT2PERSON",
                                      "CONTEXT12PERSON"],
                                 context=True)
        data = resource.select(["first_name"], limit=None)
        items = data["rows"]
        self.assertEqual(len(items), 3)
        names = [item.values()[0] for item in items]
        self.assertTrue("Context1" in names)
        self.assertTrue("Context2" in names)
        self.assertTrue("Context12" in names)

        # Global context filter 1
        s3db.context = S3FieldSelector("(organisation)$uuid").belongs(["CONTEXTORG1"])

        resource = s3db.resource("org_office",
                                 uid=["CONTEXT1OFFICE1",
                                      "CONTEXT1OFFICE2",
                                      "CONTEXT2OFFICE1"],
                                 context=True)
        data = resource.select(["name"], limit=None)
        items = data["rows"]
        self.assertEqual(len(items), 2)
        names = [item.values()[0] for item in items]
        self.assertTrue("Context1Office1" in names)
        self.assertTrue("Context1Office2" in names)
        self.assertFalse("Context2Office1" in names)

        resource = s3db.resource("pr_person",
                                 uid=["CONTEXT1PERSON",
                                      "CONTEXT2PERSON",
                                      "CONTEXT12PERSON"],
                                 context=True)
        data = resource.select(["first_name"], limit=None)
        items = data["rows"]
        self.assertEqual(len(items), 2)
        names = [item.values()[0] for item in items]
        self.assertTrue("Context1" in names)
        self.assertFalse("Context2" in names)
        self.assertTrue("Context12" in names)
        
        # Global context filter 2
        s3db.context = S3FieldSelector("(organisation)$uuid").belongs(["CONTEXTORG2"])
        
        resource = s3db.resource("org_office",
                                 uid=["CONTEXT1OFFICE1",
                                      "CONTEXT1OFFICE2",
                                      "CONTEXT2OFFICE1"],
                                 context=True)
        data = resource.select(["name"], limit=None)
        items = data["rows"]
        self.assertEqual(len(items), 1)
        names = [item.values()[0] for item in items]
        self.assertFalse("Context1Office1" in names)
        self.assertFalse("Context1Office2" in names)
        self.assertTrue("Context2Office1" in names)

        resource = s3db.resource("pr_person",
                                 uid=["CONTEXT1PERSON",
                                      "CONTEXT2PERSON",
                                      "CONTEXT12PERSON"],
                                 context=True)
        data = resource.select(["first_name"], limit=None)
        items = data["rows"]
        self.assertEqual(len(items), 2)
        names = [item.values()[0] for item in items]
        self.assertFalse("Context1" in names)
        self.assertTrue("Context2" in names)
        self.assertTrue("Context12" in names)

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.s3db.context = None
        current.db.rollback()
        current.auth.override = False

# =============================================================================
class URLQuerySerializerTests(unittest.TestCase):
    """ Test URL serialization of resource queries """

    # -------------------------------------------------------------------------
    def testSerializeURLQuerySimpleString(self):
        """ Simple string comparison serialization """

        FS = S3FieldSelector
        q = FS("person.first_name") == "Test"

        u = q.serialize_url()
        k = "person.first_name"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test")

    # -------------------------------------------------------------------------
    def testSerializeURLQueryWildcardString(self):
        """ Wildcard string comparison serialization """

        FS = S3FieldSelector
        q = FS("person.first_name").lower().like("Test%")

        u = q.serialize_url()
        k = "person.first_name__like"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test*")

    # -------------------------------------------------------------------------
    def testSerializeURLQueryMultiSelectorMatch(self):
        """ Wildcard string comparison serialization, multiple selectors """

        FS = S3FieldSelector
        q = (FS("person.first_name").lower().like("Test%")) | \
            (FS("person.last_name").lower().like("Test%"))

        u = q.serialize_url()
        k = "person.first_name|person.last_name__like"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test*")

    # -------------------------------------------------------------------------
    def testSerializeURLQueryMultiSelectorValueMismatch(self):
        """ Wildcard string comparison serialization, multiple selectors, value mismatch """

        FS = S3FieldSelector
        q = (FS("person.first_name").lower().like("Test%")) | \
            (FS("person.last_name").lower().like("Other%"))

        u = q.serialize_url()
        k = "person.first_name|person.last_name__like"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertFalse(k in u)

    # -------------------------------------------------------------------------
    def testSerializeURLQueryMultiSelectorOperatorMismatch(self):
        """ Wildcard string comparison serialization, multiple selectors, operator mismatch """

        FS = S3FieldSelector
        q = (FS("person.first_name").lower().like("Test%")) | \
            (~(FS("person.last_name").lower().like("Test%")))

        u = q.serialize_url()
        k = "person.first_name|person.last_name__like"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertFalse(k in u)

    # -------------------------------------------------------------------------
    def testSerializeURLQueryMultiSelectorMatchNegated(self):
        """ Wildcard string comparison serialization, multiple selectors, negation """

        FS = S3FieldSelector
        q = (~(FS("person.first_name").lower().like("Test%"))) | \
            (~(FS("person.last_name").lower().like("Test%")))

        u = q.serialize_url()
        k = "person.first_name|person.last_name__like!"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test*")

    # -------------------------------------------------------------------------
    def testSerializeURLQueryAlternativeValues(self):
        """ Wildcard string comparison serialization, alternative values, OR """

        FS = S3FieldSelector
        q = (FS("person.first_name").lower().like("Test%")) | \
            (FS("person.first_name").lower().like("Other%"))

        u = q.serialize_url()
        k = "person.first_name__like"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test*,Other*")

    # -------------------------------------------------------------------------
    def testSerializeURLQueryAlternativeValuesSingleOperator(self):
        """ Wildcard string comparison serialization, alternative values, single operator """

        FS = S3FieldSelector
        q = FS("first_name").like(["Test%", "Other%"])

        resource = current.s3db.resource("pr_person")
        u = q.serialize_url(resource=resource)
        # Field selector does not use a prefix, but master resource
        # is known, so should be using ~ wildcard here
        k = "~.first_name__like"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test*,Other*")

    # -------------------------------------------------------------------------
    def testSerializeURLQueryListContainmentOperator(self):
        """ Wildcard string comparison serialization, alternative values, containment operator """

        FS = S3FieldSelector
        q = FS("person.first_name").belongs(["Test", "Other"])

        u = q.serialize_url()
        k = "person.first_name__belongs"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test,Other")

# =============================================================================
class URLFilterSerializerTests(unittest.TestCase):
    """ Test URL serialization of resource filter """

    # -------------------------------------------------------------------------
    def testSerializeURLFilterEcho(self):
        """ Check that parse->serialize echoes the original URL filter """

        url_query = {"project.organisation_id$name__like": "*test*",
                     "task.description__like!": "*test*"}

        resource = current.s3db.resource("project_project", vars=url_query)

        rfilter = resource.rfilter
        url_vars = rfilter.serialize_url()
        self.assertEqual(len(url_vars), len(url_query))
        for k in url_query:
            self.assertTrue(k in url_vars)
            self.assertEqual(url_vars[k], url_query[k])

    # -------------------------------------------------------------------------
    def testSerializeURLFilter(self):
        """ Check serialization of a back-end-constructed resource filter """

        resource = current.s3db.resource("pr_person")

        FS = S3FieldSelector
        q = FS("first_name").like(["Test%", "Other%"])
        resource.add_filter(q)

        rfilter = resource.rfilter
        u = rfilter.serialize_url()

        # Field selector does not use a prefix, but master resource
        # is known (from rfilter), so should be using ~ wildcard here
        k = "~.first_name__like"
        self.assertNotEqual(u, None)
        self.assertTrue(isinstance(u, Storage))
        self.assertTrue(k in u)
        self.assertEqual(len(u.keys()), 1)
        self.assertEqual(u[k], "Test*,Other*")

# =============================================================================
class ResourceFieldTests(unittest.TestCase):
    """ Test field selector resolution with S3ResourceField """

    # -------------------------------------------------------------------------
    def testResolveContextSimple(self):

        s3db = current.s3db

        org_office = s3db.org_office
        org_organisation = s3db.org_organisation

        resource = s3db.resource("org_office")
        resource.configure(context = {"organisation": "organisation_id"})

        selector = "(organisation)$name"

        f = S3ResourceField(resource, selector)
        
        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(str(f.field), "org_organisation.name")
        self.assertEqual(f.tname, "org_organisation")
        self.assertEqual(f.fname, "name")
        self.assertEqual(f.colname, "org_organisation.name")

        tname = f.tname

        # Check join
        join = f.join
        self.assertTrue(isinstance(join, Storage))
        self.assertTrue(tname in join)
        expected = (org_office.organisation_id == org_organisation.id)
        self.assertEqual(str(join[tname]), str(expected))

        # Check left join
        left = f.left
        self.assertTrue(isinstance(join, Storage))
        self.assertTrue(tname in left)
        self.assertTrue(isinstance(left[tname], list))

        expected = org_organisation.on(org_office.organisation_id == org_organisation.id)
        self.assertEqual(len(f.left[tname]), 1)
        self.assertEqual(str(f.left[tname][0]), str(expected))

        # Check distinct
        self.assertTrue(f.distinct)
        
    # -------------------------------------------------------------------------
    def testResolveContextComplex(self):

        s3db = current.s3db

        hrm_human_resource = s3db.hrm_human_resource
        org_organisation = s3db.org_organisation
        
        resource = current.s3db.resource("pr_person")
        resource.configure(context = {"organisation": "person_id:hrm_human_resource.organisation_id"})

        selector = "(organisation)$name"

        f = S3ResourceField(resource, selector)

        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(str(f.field), "org_organisation.name")
        self.assertEqual(f.tname, "org_organisation")
        self.assertEqual(f.fname, "name")
        self.assertEqual(f.colname, "org_organisation.name")

        tname = f.tname

        # Check join
        join = f.join
        self.assertTrue(isinstance(join, Storage))
        self.assertTrue(tname in join)
        expected = (hrm_human_resource.organisation_id == org_organisation.id)
        self.assertEqual(str(join[tname]), str(expected))

        # Check left join
        left = f.left
        self.assertTrue(isinstance(join, Storage))
        self.assertTrue(tname in left)
        self.assertTrue(isinstance(left[tname], list))

        expected = org_organisation.on(hrm_human_resource.organisation_id == org_organisation.id)
        self.assertEqual(len(f.left[tname]), 1)
        self.assertEqual(str(f.left[tname][0]), str(expected))

        # Check distinct
        self.assertTrue(f.distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testResolveSelectorInnerField(self):
        """ Resolution of a selector for a field in master table """

        resource = current.s3db.resource("project_project")
        selector = "name"

        f = S3ResourceField(resource, selector)

        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(str(f.field), "project_project.name")
        self.assertEqual(str(f.tname), "project_project")
        self.assertEqual(str(f.fname), "name")
        self.assertEqual(str(f.colname), "project_project.name")

        # Check join (no join)
        self.assertEqual(f.join, Storage())
        self.assertEqual(f.left, Storage())

        # Check distinct (no join - no distinct)
        self.assertFalse(f.distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testResolveMasterWildcard(self):
        """ Resolution of a selector with a master wildcard """

        resource = current.s3db.resource("org_organisation")
        selector = "~.name"

        f = S3ResourceField(resource, selector)
        self.assertNotEqual(f, None)

        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(str(f.field), "org_organisation.name")
        self.assertEqual(str(f.tname), "org_organisation")
        self.assertEqual(str(f.fname), "name")
        self.assertEqual(str(f.colname), "org_organisation.name")

        # Check join (no join)
        self.assertEqual(f.join, Storage())
        self.assertEqual(f.left, Storage())

        # Check distinct (no join - no distinct)
        self.assertFalse(f.distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testResolveSelectorVirtualField(self):
        """ Resolution of a selector for a virtual field in master table """

        resource = current.s3db.resource("project_project")
        selector = "virtual"

        f = S3ResourceField(resource, selector)
        self.assertNotEqual(f, None)

        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(f.field, None)
        self.assertEqual(str(f.tname), "project_project")
        self.assertEqual(str(f.fname), "virtual")
        self.assertEqual(str(f.colname), "project_project.virtual")

        # Check join (no join)
        self.assertEqual(f.join, Storage())
        self.assertEqual(f.left, Storage())

        # No join - no distinct
        self.assertFalse(f.distinct)

    # -------------------------------------------------------------------------
    def testResolveSelectorComponentField(self):
        """ Resolution of a selector for a field in a component """

        s3db = current.s3db

        pr_identity = s3db.pr_identity
        pr_person = s3db.pr_person

        resource = s3db.resource("pr_person")
        selector = "identity.value"

        f = S3ResourceField(resource, selector)
        self.assertNotEqual(f, None)

        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(str(f.field), "pr_identity.value")
        self.assertEqual(str(f.tname), "pr_identity")
        self.assertEqual(str(f.fname), "value")
        self.assertEqual(str(f.colname), "pr_identity.value")

        # Check join
        self.assertTrue(isinstance(f.left["pr_identity"], list))
        self.assertEqual(len(f.left["pr_identity"]), 1)
        expected = pr_identity.on(
                        (pr_identity.person_id == pr_person.id) &
                        (pr_identity.deleted != True))
        self.assertEqual(str(f.left["pr_identity"][0]), str(expected))

        expected = (pr_identity.person_id == pr_person.id) & \
                   (pr_identity.deleted != True)
        self.assertEqual(str(f.join["pr_identity"]), str(expected))

        # Check distinct
        self.assertTrue(f.distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testResolveSelectorLinkedTableField(self):
        """ Resolution of a selector for a field in a link-table component """

        s3db = current.s3db

        project_project = s3db.project_project
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        resource = s3db.resource("project_project")
        selector = "task.description"

        f = S3ResourceField(resource, selector)
        self.assertNotEqual(f, None)

        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(str(f.field), "project_task.description")
        self.assertEqual(str(f.tname), "project_task")
        self.assertEqual(str(f.fname), "description")
        self.assertEqual(str(f.colname), "project_task.description")

        # Check join
        self.assertTrue(isinstance(f.left["project_task"], list))
        self.assertEqual(len(f.left["project_task"]), 2)

        expected_l = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))

        expected_r = project_task.on(
                        project_task_project.task_id == project_task.id)

        self.assertEqual(str(f.left["project_task"][0]), str(expected_l))
        self.assertEqual(str(f.left["project_task"][1]), str(expected_r))

        expected = ((project_task_project.deleted != True) &
                    ((project_task_project.project_id == project_project.id) &
                     (project_task_project.task_id == project_task.id)))
        self.assertEqual(str(f.join["project_task"]), str(expected))

        # Check distinct
        self.assertTrue(f.distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testResolveSelectorReferencedTableField(self):
        """ Resolution of a selector for a field in a referenced table """

        s3db = current.s3db

        project_project = s3db.project_project
        org_organisation = s3db.org_organisation

        resource = s3db.resource("project_project")
        selector = "organisation_id$name"

        f = S3ResourceField(resource, selector)
        self.assertNotEqual(f, None)

        # Check field
        self.assertEqual(f.selector, selector)
        self.assertEqual(str(f.field), "org_organisation.name")
        self.assertEqual(str(f.tname), "org_organisation")
        self.assertEqual(str(f.fname), "name")
        self.assertEqual(str(f.colname), "org_organisation.name")

        # Check join
        self.assertTrue(isinstance(f.left["org_organisation"], list))
        self.assertEqual(len(f.left["org_organisation"]), 1)
        expected = org_organisation.on(
                    project_project.organisation_id == org_organisation.id)
        self.assertEqual(str(f.left["org_organisation"][0]), str(expected))

        expected = (project_project.organisation_id == org_organisation.id)
        self.assertEqual(str(f.join["org_organisation"]), str(expected))

        # Check distinct
        self.assertTrue(f.distinct)

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testResolveSelectorExceptions(self):
        """ Exception for invalid selectors """

        resource = current.s3db.resource("project_project")
        selector = "organisation_id.test"
        self.assertRaises(AttributeError, S3ResourceField, resource, selector)

# =============================================================================
class ResourceDataAccessTests(unittest.TestCase):
    """ Test data access via resources """

    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):

        s3db = current.s3db
        current.auth.override = True

        xmlstr = """
<s3xml>
    <resource name="org_organisation" uuid="DATESTORG">
        <data field="name">DATestOrg</data>
        <resource name="org_office" uuid="DATESTOFFICE1">
            <data field="name">DATestOffice1</data>
        </resource>
        <resource name="org_office" uuid="DATESTOFFICE2">
            <data field="name">DATestOffice2</data>
        </resource>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))
        resource = s3db.resource("org_organisation")
        resource.import_xml(xmltree)

    # -------------------------------------------------------------------------
    def testResourceFieldExtract(self):
        """ Test value extraction from rows by S3ResourceFields """

        s3db = current.s3db

        resource = s3db.resource("org_organisation",
                                 uid="DATESTORG")

        rows = resource.select(["name", "office.name"],
                               limit=1, as_rows=True)
        self.assertEqual(len(rows), 2)
        row = rows[0]

        rf = S3ResourceField(resource, "name")
        value = rf.extract(row)
        self.assertEqual(value, "DATestOrg")

        rf = S3ResourceField(resource, "office.name")
        value = rf.extract(row)
        self.assertEqual(value[:-1], "DATestOffice")

    # -------------------------------------------------------------------------
    def testResourceJSON(self):
        """ Test simple JSON export of a resource """

        s3db = current.s3db
        resource = s3db.resource("org_organisation", uid="DATESTORG")
        jstr = resource.json(["name", "office.name"])

        from gluon.contrib import simplejson as json
        data = json.loads(jstr)
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 1)
        record = data[0]
        self.assertTrue("org_organisation.name" in record)
        self.assertTrue("org_office.name" in record)
        self.assertTrue(isinstance(record["org_office.name"], list))
        self.assertEqual(len(record["org_office.name"]), 2)
        self.assertTrue("DATestOffice1" in record["org_office.name"])
        self.assertTrue("DATestOffice2" in record["org_office.name"])
        self.assertEqual(record["org_organisation.name"], "DATestOrg")

    # -------------------------------------------------------------------------
    def testCollapseRows(self):
        """ Test correct handling of ambiguous rows in select """

        s3db = current.s3db

        otable = s3db.org_organisation
        ftable = s3db.org_office
        query = (otable.uuid == "DATESTORG") & \
                (ftable.organisation_id == otable.id)

        rows = current.db(query).select(otable.id,
                                        otable.name,
                                        ftable.id,
                                        ftable.name)
        self.assertEqual(len(rows), 2)

        resource = s3db.resource("org_organisation", uid="DATESTORG")
        list_fields = ["name", "office.name"]
        
        rows = resource.select(list_fields)["rows"]
        self.assertEqual(len(rows), 1)

        office_names = rows[0]["org_office.name"]
        self.assertTrue(isinstance(office_names, list))
        self.assertEqual(len(office_names), 2)
        self.assertTrue("DATestOffice1" in office_names)
        self.assertTrue("DATestOffice2" in office_names)

        rows = resource.select(list_fields,
                                    represent=True)["rows"]
        self.assertEqual(len(rows), 1)

        office_names = rows[0]["org_office.name"]
        self.assertTrue(isinstance(office_names, basestring))
        office_names = [s.strip() for s in office_names.split(",")]
        self.assertEqual(len(office_names), 2)
        self.assertTrue("DATestOffice1" in office_names)
        self.assertTrue("DATestOffice2" in office_names)

    # -------------------------------------------------------------------------
    def testLoadRows(self):
        """ Test loading rows with ambiguous query """

        s3db = current.s3db

        # This filter query produces ambiguous rows (=the same
        # organisation record appears once for each office):
        query = (S3FieldSelector("office.name").like("DATestOffice%"))

        # load() should not load any duplicate rows
        resource = s3db.resource("org_organisation")
        resource.add_filter(query)
        resource.load()
        self.assertEqual(len(resource), 1)
        self.assertEqual(len(resource._rows), 1)
        self.assertEqual(resource._length, 1)

        # Try the same with an additional virtual field filter:
        query = query & (S3FieldSelector("testfield") == "TEST")

        # Should still not give any duplicates:
        resource = s3db.resource("org_organisation")
        class FakeVirtualFields(object):
            def testfield(self):
                return "TEST"
        resource.table.virtualfields.append(FakeVirtualFields())
        resource.add_filter(query)
        resource.load()
        self.assertEqual(len(resource), 1)
        self.assertEqual(len(resource._rows), 1)
        self.assertEqual(resource._length, 1)

    # -------------------------------------------------------------------------
    def testLoadIds(self):
        """ Test loading IDs with ambiguous query """

        s3db = current.s3db

        # This filter query produces ambiguous rows (=the same
        # organisation record appears once for each office):
        query = (S3FieldSelector("office.name").like("DATestOffice%"))

        # load() should not load any duplicate rows
        resource = s3db.resource("org_organisation")
        resource.add_filter(query)
        uid = resource.get_uid()
        self.assertTrue(isinstance(uid, str))
        self.assertEqual(uid, "DATESTORG")

        # Try the same with an additional virtual field filter:
        query = query & (S3FieldSelector("testfield") == "TEST")

        # Should still not give any duplicates:
        resource = s3db.resource("org_organisation")
        class FakeVirtualFields(object):
            def testfield(self):
                return "TEST"
        resource.table.virtualfields.append(FakeVirtualFields())
        resource.add_filter(query)
        uid = resource.get_uid()
        self.assertTrue(isinstance(uid, str))
        self.assertEqual(uid, "DATESTORG")

    # -------------------------------------------------------------------------
    def testCountRows(self):
        """ Test counting rows with ambiguous query """

        s3db = current.s3db

        # This filter query produces ambiguous rows (=the same
        # organisation record appears once for each office):
        query = (S3FieldSelector("office.name").like("DATestOffice%"))

        # count() should properly deduplicate the rows before counting them
        resource = s3db.resource("org_organisation")
        resource.add_filter(query)
        self.assertEqual(resource.count(), 1)

        # Try the same with an additional virtual field filter:
        query = query & (S3FieldSelector("testfield") == "TEST")

        # Should still not give any duplicates:
        resource = s3db.resource("org_organisation")
        class FakeVirtualFields(object):
            def testfield(self):
                return "TEST"
        resource.table.virtualfields.append(FakeVirtualFields())
        resource.add_filter(query)
        self.assertEqual(resource.count(), 1)

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):

        current.db.rollback()
        current.auth.override = False

# =============================================================================
class ResourceAxisFilterTests(unittest.TestCase):
    """ Test Axis Filters """

    def testListTypeFilter(self):
        """ Test list:type axis value filtering """

        tablename = "axis_filter"
        db = current.db
        db.define_table(tablename,
                        Field("facility_type_id",
                              "list:reference org_facility_type"),
                        *s3_meta_fields())
        table = db[tablename]

        try:

            s3db = current.s3db

            resource = s3db.resource(tablename)
            q = (S3FieldSelector("facility_type_id").contains([1,2,3])) & \
                (~(S3FieldSelector("facility_type_id") == 2))
            resource.add_filter(q)
            query = resource.get_query()
            af = S3AxisFilter(query.as_dict(flat=True), tablename)

            rfield = S3ResourceField(resource, "facility_type_id")

            values, ignore = af.values(rfield)
            self.assertTrue("1" in values)
            self.assertFalse("2" in values)
            self.assertTrue("3" in values)

            resource = s3db.resource(tablename)
            q = (S3FieldSelector("facility_type_id").contains([1,2,3])) & \
                (~(S3FieldSelector("facility_type_id") != 2))
            resource.add_filter(q)
            query = resource.get_query()
            af = S3AxisFilter(query.as_dict(flat=True), tablename)

            values, ignore = af.values(rfield)
            self.assertTrue("1" in values)
            self.assertTrue("2" in values)
            self.assertTrue("3" in values)

            resource = s3db.resource(tablename)
            q = (S3FieldSelector("facility_type_id").contains([1,2,3])) | \
                (~(S3FieldSelector("facility_type_id") == 2))
            resource.add_filter(q)
            query = resource.get_query()
            af = S3AxisFilter(query.as_dict(flat=True), tablename)

            values, ignore = af.values(rfield)
            self.assertTrue("1" in values)
            self.assertTrue("2" in values)
            self.assertTrue("3" in values)

            resource = s3db.resource(tablename)
            q = (S3FieldSelector("facility_type_id").contains([1,2,3])) | \
                (~(S3FieldSelector("facility_type_id") != 2))
            resource.add_filter(q)
            query = resource.get_query()
            af = S3AxisFilter(query.as_dict(flat=True), tablename)

            values, ignore = af.values(rfield)
            self.assertTrue("1" in values)
            self.assertTrue("2" in values)
            self.assertTrue("3" in values)
            
        finally:
            try:
                table.drop()
            except:
                pass

# =============================================================================
class ResourceDataTableFilterTests(unittest.TestCase):
    """ Test datatable_filter """

    # -------------------------------------------------------------------------
    def testDataTableFilterStandard(self):
        """ Test Standard Data Table """
        
        resource = current.s3db.resource("hrm_certificate_skill")
        vars = Storage({"bSortable_0": "false",
                        "bSortable_1": "true",
                        "bSortable_2": "true",
                        "sSortDir_0": "asc",
                        "iSortCol_0": "1",
                        "iColumns": "3",
                        "iSortingCols": "1"})
        searchq, orderby, left = resource.datatable_filter(["id",
                                                            "skill_id",
                                                            "competency_id"],
                                                            vars)
        self.assertEqual(orderby, "hrm_skill.name asc")

    # -------------------------------------------------------------------------
    def testDataTableFilterWithBulkColumn(self):
        """ Test De-Duplicator Data Table """
        
        resource = current.s3db.resource("hrm_certificate_skill")
        vars = Storage({"bSortable_0": "false",
                        "bSortable_1": "false",
                        "bSortable_2": "true",
                        "bSortable_3": "true",
                        "sSortDir_0": "desc",
                        "iSortCol_0": "2",
                        "iColumns": "4",
                        "iSortingCols": "1"})
        searchq, orderby, left = resource.datatable_filter(["id",
                                                            "skill_id",
                                                            "competency_id"],
                                                            vars)
        self.assertEqual(orderby, "hrm_skill.name desc")

    # -------------------------------------------------------------------------
    def testDataTableFilterOther(self):
        """ Test Other Data Table """
        
        resource = current.s3db.resource("hrm_certificate_skill")
        vars = Storage({"bSortable_0": "false",
                        "bSortable_1": "true",
                        "bSortable_2": "false",
                        "bSortable_3": "true",
                        "sSortDir_0": "desc",
                        "iSortCol_0": "3",
                        "iColumns": "4",
                        "iSortingCols": "1"})
        searchq, orderby, left = resource.datatable_filter(["id",
                                                            "skill_id",
                                                            "competency_id"],
                                                            vars)
        self.assertEqual(orderby, "hrm_competency_rating.priority desc")
        
# =============================================================================
class ResourceExportTests(unittest.TestCase):
    """ Test XML export of resources """

    # -------------------------------------------------------------------------
    def testExportTree(self):
        """ Test export of a resource as element tree """

        xml = current.xml
        auth = current.auth

        auth.override = True
        
        xmlstr = """
<s3xml>
    <resource name="org_organisation">
        <data field="name">TestExportTreeOrganisation1</data>
        <resource name="org_office" uuid="ETO1">
            <data field="name">TestExportTreeOffice1</data>
        </resource>
    </resource>
</s3xml>"""

        try:
            xmltree = etree.ElementTree(etree.fromstring(xmlstr))
            resource = current.s3db.resource("org_organisation")
            resource.import_xml(xmltree)

            resource = current.s3db.resource("org_office", uid="ETO1")
            tree = resource.export_tree(start=0, limit=1, dereference=False)

            root = tree.getroot()
            self.assertEqual(root.tag, xml.TAG.root)

            attrib = root.attrib
            self.assertEqual(len(attrib), 5)
            self.assertEqual(attrib["success"], "true")
            self.assertEqual(attrib["start"], "0")
            self.assertEqual(attrib["limit"], "1")
            self.assertEqual(attrib["results"], "1")
            self.assertTrue("url" in attrib)

            self.assertEqual(len(root), 1)
            for child in root:
                self.assertEqual(child.tag, xml.TAG.resource)
                attrib = child.attrib
                self.assertEqual(attrib["name"], "org_office")
                self.assertTrue("uuid" in attrib)
        finally:
            current.db.rollback()
            auth.override = False

    # -------------------------------------------------------------------------
    def testExportTreeWithMaxBounds(self):
        """ Text XML output with max bounds """

        xml = current.xml
        auth = current.auth

        auth.override = True

        xmlstr = """
<s3xml>
    <resource name="org_organisation">
        <data field="name">TestExportTreeOrganisation2</data>
        <resource name="org_office" uuid="ETO2">
            <data field="name">TestExportTreeOffice2</data>
        </resource>
    </resource>
</s3xml>"""

        try:
            xmltree = etree.ElementTree(etree.fromstring(xmlstr))
            resource = current.s3db.resource("org_organisation")
            resource.import_xml(xmltree)

            resource = current.s3db.resource("org_office", uid="ETO2")
            tree = resource.export_tree(start=0,
                                        limit=1,
                                        dereference=False,
                                        maxbounds=True)
            root = tree.getroot()
            attrib = root.attrib
            self.assertEqual(len(attrib), 9)
            self.assertTrue("latmin" in attrib)
            self.assertTrue("latmax" in attrib)
            self.assertTrue("lonmin" in attrib)
            self.assertTrue("lonmax" in attrib)

        finally:
            current.db.rollback()
            auth.override = False

    # -------------------------------------------------------------------------
    def testExportTreeWithMSince(self):
        """ Test automatic ordering of export items by mtime if msince is given """

        auth = current.auth
        auth.override = True

        xmlstr = """
<s3xml>
    <resource name="hms_hospital" uuid="ORDERTESTHOSPITAL1">
        <data field="name">OrderTestHospital1</data>
    </resource>
    <resource name="hms_hospital" uuid="ORDERTESTHOSPITAL2">
        <data field="name">OrderTestHospital2</data>
    </resource>
</s3xml>"""

        try:
            xmltree = etree.ElementTree(etree.fromstring(xmlstr))
            resource = current.s3db.resource("hms_hospital")
            resource.import_xml(xmltree)

            resource = current.s3db.resource(resource,
                                            uid=["ORDERTESTHOSPITAL1",
                                                "ORDERTESTHOSPITAL2"])
            resource.load(limit=2)
            self.assertEqual(len(resource), 2)
            first = resource._rows[0]["uuid"]
            last = resource._rows[1]["uuid"]

            import time
            time.sleep(2) # Wait 2 seconds to change mtime
            resource._rows[0].update_record(name="OrderTestHospital1")

            msince = msince=datetime.datetime.utcnow() - datetime.timedelta(days=1)

            tree = resource.export_tree(start=0,
                                        limit=1,
                                        dereference=False)
            root = tree.getroot()
            self.assertEqual(len(root), 1)

            child = root[0]
            uuid = child.get("uuid", None)
            self.assertEqual(uuid, first)

            tree = resource.export_tree(start=0,
                                        limit=1,
                                        msince=msince,
                                        dereference=False)
            root = tree.getroot()
            self.assertEqual(len(root), 1)

            child = root[0]
            uuid = child.get("uuid", None)
            self.assertEqual(uuid, last)

        finally:
            current.db.rollback()
            auth.override = False

    # -------------------------------------------------------------------------
    def testExportXMLWithSyncFilters(self):
        """ Test XML Export with Sync Filters """

        auth = current.auth
        s3db = current.s3db
        
        auth.override = True

        xmlstr = """
<s3xml>
    <resource name="org_office_type" uuid="SFT1">
        <data field="name">SFT1</data>
    </resource>
    <resource name="org_office_type" uuid="SFT2">
        <data field="name">SFT2</data>
    </resource>
    <resource name="org_organisation" uuid="SFO1">
        <data field="name">Sync1FilterOrganisation</data>
        <resource name="org_office" uuid="S1FO1">
            <data field="name">Sync1FilterOffice1</data>
            <reference field="office_type_id" resource="org_office_type" uuid="SFT1"/>
        </resource>
    </resource>
    <resource name="org_organisation" uuid="SFO2">
        <data field="name">Sync2FilterOrganisation</data>
        <resource name="org_office" uuid="S1FO2">
            <data field="name">Sync1FilterOffice2</data>
            <reference field="office_type_id" resource="org_office_type" uuid="SFT2"/>
        </resource>
    </resource>
    <resource name="org_organisation" uuid="SFO3">
        <data field="name">Sync3FilterOrganisation</data>
        <resource name="org_office" uuid="S1FO3">
            <data field="name">Sync1FilterOffice3</data>
        </resource>
        <resource name="org_office" uuid="S2FO1">
            <data field="name">Sync2FilterOffice1</data>
        </resource>
    </resource>
</s3xml>"""

        try:
            xmltree = etree.ElementTree(etree.fromstring(xmlstr))
            resource = current.s3db.resource("org_organisation")
            resource.import_xml(xmltree)

            # Filter master by master field
            resource = s3db.resource(resource,
                                     uid=["SFO1", "SFO2", "SFO3"])

            filters = {"org_organisation": {"organisation.name__like": "Sync1%"}}

            xmlexport = resource.export_xml(filters=filters,
                                            mcomponents=["org_office"],
                                            dereference=False)
                                            
            xmltree = etree.ElementTree(etree.fromstring(xmlexport))
            orgs = xmltree.xpath("resource[@name='org_organisation']")
            self.assertEqual(len(orgs), 1)
            self.assertEqual(orgs[0].get("uuid"), "SFO1")

            offices = xmltree.xpath("//resource[@name='org_office']")
            self.assertEqual(len(offices), 1)
            self.assertEqual(offices[0].get("uuid"), "S1FO1")

            # Filter master by component field
            resource = s3db.resource(resource,
                                     uid=["SFO1", "SFO2", "SFO3"])

            filters = {"org_organisation": {"office.name__like": "Sync2%"}}

            xmlexport = resource.export_xml(filters=filters,
                                            mcomponents=["org_office"],
                                            dereference=False)

            xmltree = etree.ElementTree(etree.fromstring(xmlexport))
            orgs = xmltree.xpath("resource[@name='org_organisation']")
            self.assertEqual(len(orgs), 1)
            self.assertEqual(orgs[0].get("uuid"), "SFO3")

            offices = xmltree.xpath("//resource[@name='org_office']")
            self.assertEqual(len(offices), 1)
            self.assertEqual(offices[0].get("uuid"), "S2FO1")

            # Filter component by component field
            resource = s3db.resource(resource,
                                     uid=["SFO1", "SFO2", "SFO3"])

            filters = {"org_office": {"office.name__like": "Sync1%"}}

            xmlexport = resource.export_xml(filters=filters,
                                            mcomponents=["org_office"],
                                            dereference=False)
            xmltree = etree.ElementTree(etree.fromstring(xmlexport))

            orgs = xmltree.xpath("resource[@name='org_organisation']")
            self.assertEqual(len(orgs), 3)
            uids = [org.get("uuid") for org in orgs]
            self.assertTrue("SFO1" in uids)
            self.assertTrue("SFO2" in uids)
            self.assertTrue("SFO3" in uids)
            
            offices = xmltree.xpath("//resource[@name='org_office']")
            self.assertEqual(len(offices), 3)
            uids = [office.get("uuid") for office in offices]
            self.assertTrue("S1FO1" in uids)
            self.assertTrue("S1FO2" in uids)
            self.assertTrue("S1FO3" in uids)
            self.assertFalse("S2FO1" in uids)

            # Filter referenced table
            resource = s3db.resource(resource,
                                     uid=["SFO1", "SFO2"])

            xmlexport = resource.export_xml(filters=None,
                                            mcomponents=["org_office"])
            xmltree = etree.ElementTree(etree.fromstring(xmlexport))

            types = xmltree.xpath("resource[@name='org_office_type']")
            self.assertEqual(len(types), 2)
            uids = [t.get("uuid") for t in types]
            self.assertTrue("SFT1" in uids)
            self.assertTrue("SFT2" in uids)

            resource = s3db.resource(resource,
                                     uid=["SFO1", "SFO2"])

            filters = {"org_office_type": {"office_type.name__like": "SFT1%"}}

            xmlexport = resource.export_xml(filters=filters,
                                            mcomponents=["org_office"])
            xmltree = etree.ElementTree(etree.fromstring(xmlexport))

            types = xmltree.xpath("resource[@name='org_office_type']")
            self.assertEqual(len(types), 1)
            self.assertEqual(types[0].get("uuid"), "SFT1")

        finally:
            current.db.rollback()
            auth.override = False

# =============================================================================
class ResourceImportTests(unittest.TestCase):
    """ Test XML imports into resources """

    @classmethod
    def setUpClass(cls):

        current.auth.override = True

    # -------------------------------------------------------------------------
    def testImportXML(self):
        """ Test JSON message after XML import """

        xmlstr = """
<s3xml>

    <resource name="pr_person">

        <data field="first_name">Jason</data>
        <data field="last_name">Test</data>
        <data field="initials">JT</data>
        <data field="date_of_birth" value="1922-03-15"/>

        <resource name="pr_contact">
            <data field="contact_method">EMAIL</data>
            <data field="value">json@example.com</data>
        </resource>

        <resource name="pr_contact">
            <data field="contact_method">SMS</data>
            <data field="value">+123456789</data>
        </resource>

    </resource>

</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))
        
        resource = current.s3db.resource("pr_person")
        msg = resource.import_xml(xmltree)
        
        from gluon.contrib import simplejson as json
        msg = json.loads(msg)

        self.assertEqual(msg["status"], "success")
        self.assertEqual(msg["statuscode"], "200")
        self.assertEqual(msg["records"], 1)
        self.assertTrue("created" in msg)
        self.assertTrue(isinstance(msg["created"], list))
        self.assertTrue(len(msg["created"]) == 1)

    # -------------------------------------------------------------------------
    def testImportXMLWithMTime(self):
        """ Test mtime update in imports """

        # If mtime is given in the import XML, then resource.mtime should
        # get updated to the youngest entry
        xmlstr = """
<s3xml>
    <resource name="hms_hospital" uuid="MTIMETESTHOSPITAL1" modified_on="2012-03-31T00:00:00">
        <data field="name">MTimeTestHospital1</data>
    </resource>
    <resource name="hms_hospital" uuid="MTIMETESTHOSPITAL2" modified_on="2012-04-21T00:00:00">
        <data field="name">MTimeTestHospital2</data>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))
        resource = current.s3db.resource("hms_hospital")
        resource.import_xml(xmltree)
        self.assertEqual(current.xml.as_utc(resource.mtime),
                         current.xml.as_utc(datetime.datetime(2012, 4, 21, 0, 0, 0)))

    # -------------------------------------------------------------------------
    def testImportXMLWithoutMTime(self):
        """ Test mtime update in imports with no mtime given """

        # If no mtime is given, resource.mtime should be set to current UTC
        xmlstr = """
<s3xml>
    <resource name="hms_hospital" uuid="MTIMETESTHOSPITAL3">
        <data field="name">MTimeTestHospital3</data>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))
        resource = current.s3db.resource("hms_hospital")
        resource.import_xml(xmltree)
        # Can't compare with exactly utcnow as these would be milliseconds apart,
        # assume equal dates are sufficient for this test
        self.assertEqual(current.xml.as_utc(resource.mtime).date(),
                         current.xml.as_utc(datetime.datetime.utcnow()).date())

    # -------------------------------------------------------------------------
    def testImportXMLWithPartialMTime(self):
        """ Test mtime update in imports if mtime given in only some records """

        # If mixed, then we should still get current UTC
        xmlstr = """
<s3xml>
    <resource name="hms_hospital" uuid="MTIMETESTHOSPITAL4" modified_on="2012-03-31T00:00:00">
        <data field="name">MTimeTestHospital4</data>
    </resource>
    <resource name="hms_hospital" uuid="MTIMETESTHOSPITAL5">
        <data field="name">MTimeTestHospital5</data>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))
        resource = current.s3db.resource("hms_hospital")
        resource.import_xml(xmltree)
        self.assertEqual(current.xml.as_utc(resource.mtime).date(),
                         current.xml.as_utc(datetime.datetime.utcnow()).date())

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):

        current.db.rollback()
        current.auth.override = False

# =============================================================================
class ResourceDataObjectAPITests (unittest.TestCase):
    """ Test the S3Resource Data Object API """

    # -------------------------------------------------------------------------
    def testLoadStatusIndication(self):
        """ Test load status indication by value of _rows """

        # A newly created resource has _rows=None
        resource = current.s3db.resource("project_time")
        self.assertEqual(resource._rows, None)

        # After load(), this must always be a list
        resource.load()
        self.assertNotEqual(resource._rows, None)
        self.assertTrue(isinstance(resource._rows, list))

        # After clear(), this must be None again
        resource.clear()
        self.assertEqual(resource._rows, None)

    # -------------------------------------------------------------------------
    def testLoadFieldSelection(self):
        """ Test selection of fields in load() with fields and skip """

        s3db = current.s3db
        auth = current.auth
        auth.override = True

        xmlstr = """
<s3xml>
    <resource name="org_office" uuid="LOADTESTOFFICE">
        <data field="name">LoadTestOffice</data>
        <reference field="organisation_id" resource="org_organisation">
            <resource name="org_organisation">
                <data field="name">LoadTestOrganisation</data>
            </resource>
        </reference>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))

        try:
            resource = s3db.resource("org_office")
            resource.import_xml(xmltree)

            resource = s3db.resource("org_office", uid="LOADTESTOFFICE")

            # Restrict field selection
            rows = resource.load(fields=["name"])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertTrue(hasattr(row, "id"))
            self.assertTrue(hasattr(row, "name"))
            self.assertTrue(hasattr(row, "created_on")) # meta-field
            self.assertTrue(hasattr(row, "pe_id")) # super-key
            self.assertFalse(hasattr(row, "organisation_id"))

            # Skip field
            rows = resource.load(skip=["name"])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertTrue(hasattr(row, "id"))
            self.assertFalse(hasattr(row, "name"))
            self.assertTrue(hasattr(row, "created_on"))
            self.assertTrue(hasattr(row, "pe_id"))
            self.assertTrue(hasattr(row, "organisation_id"))

            # skip overrides fields
            rows = resource.load(fields=["name", "organisation_id"],
                                 skip=["organisation_id"])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertTrue(hasattr(row, "id"))
            self.assertTrue(hasattr(row, "name"))
            self.assertTrue(hasattr(row, "created_on"))
            self.assertTrue(hasattr(row, "pe_id"))
            self.assertFalse(hasattr(row, "organisation_id"))

            # Can't skip meta-fields
            rows = resource.load(fields=["name", "organisation_id"],
                                 skip=["created_on"])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertTrue(hasattr(row, "id"))
            self.assertTrue(hasattr(row, "name"))
            self.assertTrue(hasattr(row, "created_on"))
            self.assertTrue(hasattr(row, "pe_id"))
            self.assertTrue(hasattr(row, "organisation_id"))

            # Can't skip record ID
            rows = resource.load(fields=["name", "organisation_id"],
                                 skip=["id"])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertTrue(hasattr(row, "id"))
            self.assertTrue(hasattr(row, "name"))
            self.assertTrue(hasattr(row, "created_on"))
            self.assertTrue(hasattr(row, "pe_id"))
            self.assertTrue(hasattr(row, "organisation_id"))

            # Can't skip super-keys
            rows = resource.load(fields=["name", "organisation_id"],
                                 skip=["pe_id"])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertTrue(hasattr(row, "id"))
            self.assertTrue(hasattr(row, "name"))
            self.assertTrue(hasattr(row, "created_on"))
            self.assertTrue(hasattr(row, "pe_id"))
            self.assertTrue(hasattr(row, "organisation_id"))

        finally:
            auth.override = False
            current.db.rollback()
        
# =============================================================================
class MergeOrganisationsTests(unittest.TestCase):
    """ Test merging org_organisation records """

    # -------------------------------------------------------------------------
    def setUp(self):
        """ Set up organisation records """

        s3db = current.s3db

        otable = s3db.org_organisation

        org1 = Storage(name="Merge Test Organisation",
                       acronym="MTO",
                       country="UK",
                       website="http://www.example.org")
        org1_id = otable.insert(**org1)
        org1.update(id=org1_id)
        s3db.update_super(otable, org1)

        org2 = Storage(name="Merger Test Organisation",
                       acronym="MTOrg",
                       country="US",
                       website="http://www.example.com")
        org2_id = otable.insert(**org2)
        org2.update(id=org2_id)
        s3db.update_super(otable, org2)

        self.id1 = org1_id
        self.id2 = org2_id

        self.resource = s3db.resource("org_organisation",
                                      id=[self.id1, self.id2])
        current.auth.override = True

    # -------------------------------------------------------------------------
    def testMerge(self):
        """ Test merge """

        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)
        org1, org2 = self.get_records()

        self.assertNotEqual(org1, None)
        self.assertNotEqual(org2, None)

        self.assertFalse(org1.deleted)
        self.assertTrue(org2.deleted)
        self.assertEqual(str(self.id1), str(org2.deleted_rb))

        self.assertEqual(org1.name, "Merge Test Organisation")
        self.assertEqual(org1.acronym, "MTO")
        self.assertEqual(org1.country, "UK")
        self.assertEqual(org1.website, "http://www.example.org")

        self.assertEqual(org2.name, "Merger Test Organisation")
        self.assertEqual(org2.acronym, "MTOrg")
        self.assertEqual(org2.country, "US")
        self.assertEqual(org2.website, "http://www.example.com")

    # -------------------------------------------------------------------------
    def testMergeMissingOriginalSE(self):
        """ Test merge where original record lacks SEs """

        resource = self.resource
        get_records = self.get_records

        assertEqual = self.assertEqual
        assertNotEqual = self.assertNotEqual
        assertTrue = self.assertTrue

        org1, org2 = get_records()
        success = current.s3db.delete_super(resource.table, org1)
        assertTrue(success)
        org1, org2 = get_records()
        assertEqual(org1.pe_id, None)

        success = resource.merge(self.id1, self.id2)
        assertTrue(success)
        org1, org2 = get_records()

        assertNotEqual(org1, None)
        assertNotEqual(org2, None)

        self.assertFalse(org1.deleted)
        assertTrue(org2.deleted)
        assertEqual(str(self.id1), str(org2.deleted_rb))

        assertNotEqual(org1.pe_id, None)

    # -------------------------------------------------------------------------
    def testMergeMissingDuplicateSE(self):
        """ Test merge where duplicate record lacks SEs """

        resource = self.resource
        get_records = self.get_records

        assertEqual = self.assertEqual
        assertNotEqual = self.assertNotEqual
        assertTrue = self.assertTrue

        org1, org2 = get_records()
        success = current.s3db.delete_super(resource.table, org2)
        assertTrue(success)
        org1, org2 = get_records()
        assertEqual(org2.pe_id, None)

        success = resource.merge(self.id1, self.id2)
        assertTrue(success)
        org1, org2 = get_records()

        assertNotEqual(org1, None)
        assertNotEqual(org2, None)

        self.assertFalse(org1.deleted)
        assertTrue(org2.deleted)
        assertEqual(str(self.id1), str(org2.deleted_rb))

        assertEqual(org2.pe_id, None)

    # -------------------------------------------------------------------------
    def testMergeMissingSE(self):
        """ Test merge where both records lack SEs """

        resource = self.resource
        get_records = self.get_records

        assertEqual = self.assertEqual
        assertNotEqual = self.assertNotEqual
        assertTrue = self.assertTrue

        org1, org2 = get_records()
        success = current.s3db.delete_super(resource.table, org1)
        success = current.s3db.delete_super(resource.table, org2)
        assertTrue(success)
        org1, org2 = get_records()
        assertEqual(org1.pe_id, None)
        assertEqual(org2.pe_id, None)

        success = resource.merge(self.id1, self.id2)
        assertTrue(success)
        org1, org2 = get_records()

        assertNotEqual(org1, None)
        assertNotEqual(org2, None)

        self.assertFalse(org1.deleted)
        assertTrue(org2.deleted)
        assertEqual(str(self.id1), str(org2.deleted_rb))

        assertNotEqual(org1.pe_id, None)
        assertEqual(org2.pe_id, None)

    # -------------------------------------------------------------------------
    def testMergeReplace(self):
        """ Test merge with replace """

        success = self.resource.merge(self.id1, self.id2,
                                      replace = ["acronym", "website"])
        self.assertTrue(success)
        org1, org2 = self.get_records()

        self.assertNotEqual(org1, None)
        self.assertNotEqual(org2, None)

        self.assertFalse(org1.deleted)
        self.assertTrue(org2.deleted)
        self.assertEqual(str(self.id1), str(org2.deleted_rb))

        self.assertEqual(org1.name, "Merge Test Organisation")
        self.assertEqual(org1.acronym, "MTOrg")
        self.assertEqual(org1.country, "UK")
        self.assertEqual(org1.website, "http://www.example.com")

        self.assertEqual(org2.name, "Merger Test Organisation")
        self.assertEqual(org2.acronym, "MTOrg")
        self.assertEqual(org2.country, "US")
        self.assertEqual(org2.website, "http://www.example.com")

    # -------------------------------------------------------------------------
    def testMergeReplaceUnique(self):
        """ Test merge with replace of a unique-field """

        success = self.resource.merge(self.id1, self.id2,
                                      replace = ["name"])
        self.assertTrue(success)
        org1, org2 = self.get_records()

        self.assertNotEqual(org1, None)
        self.assertNotEqual(org2, None)

        self.assertFalse(org1.deleted)
        self.assertTrue(org2.deleted)
        self.assertEqual(str(self.id1), str(org2.deleted_rb))

        self.assertEqual(org1.name, "Merger Test Organisation")
        self.assertEqual(org2.name, "Merge Test Organisation")

    # -------------------------------------------------------------------------
    def testMergeReplaceAndUpdate(self):
        """ Test merge with replace and Update"""

        success = self.resource.merge(self.id1, self.id2,
                                      replace = ["acronym"],
                                      update = Storage(website = "http://www.example.co.uk"))
        self.assertTrue(success)
        org1, org2 = self.get_records()

        self.assertNotEqual(org1, None)
        self.assertNotEqual(org2, None)

        self.assertFalse(org1.deleted)
        self.assertTrue(org2.deleted)
        self.assertEqual(str(self.id1), str(org2.deleted_rb))

        self.assertEqual(org1.name, "Merge Test Organisation")
        self.assertEqual(org1.acronym, "MTOrg")
        self.assertEqual(org1.country, "UK")
        self.assertEqual(org1.website, "http://www.example.co.uk")

        self.assertEqual(org2.name, "Merger Test Organisation")
        self.assertEqual(org2.acronym, "MTOrg")
        self.assertEqual(org2.country, "US")
        self.assertEqual(org2.website, "http://www.example.com")

    # -------------------------------------------------------------------------
    def testMergeLinkTable(self):
        """ Test merge of link table entries """

        db = current.db
        s3db = current.s3db
        deployment_settings = current.deployment_settings

        org1, org2 = self.get_records()

        org1_pe_id = s3db.pr_get_pe_id(org1)
        org2_pe_id = s3db.pr_get_pe_id(org2)

        otable = s3db.org_organisation
        btable = s3db.org_organisation_branch

        branch1 = Storage(name="TestBranch1")
        branch1_id = otable.insert(**branch1)
        self.assertNotEqual(branch1_id, None)
        branch1.update(id=branch1_id)
        s3db.update_super(otable, branch1)
        branch1_pe_id = s3db.pr_get_pe_id(otable, branch1_id)
        self.assertNotEqual(branch1_pe_id, None)
        link1 = Storage(organisation_id=self.id1, branch_id=branch1_id)
        link1_id = btable.insert(**link1)
        s3db.pr_update_affiliations(btable, link1_id)
        ancestors = s3db.pr_get_ancestors(branch1_pe_id)
        self.assertEqual(ancestors, [str(org1_pe_id)])

        branch2 = Storage(name="TestBranch2")
        branch2_id = otable.insert(**branch2)
        self.assertNotEqual(branch2_id, None)
        branch2.update(id=branch2_id)
        s3db.update_super(otable, branch2)
        branch2_pe_id = s3db.pr_get_pe_id("org_organisation", branch2_id)
        self.assertNotEqual(branch2_pe_id, None)
        link2 = Storage(organisation_id=self.id2, branch_id=branch2_id)
        link2_id = btable.insert(**link2)
        s3db.pr_update_affiliations(btable, link2_id)
        ancestors = s3db.pr_get_ancestors(branch2_pe_id)
        self.assertEqual(ancestors, [str(org2_pe_id)])

        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)

        link1 = db(btable._id == link1_id).select(limitby=(0, 1)).first()
        link2 = db(btable._id == link2_id).select(limitby=(0, 1)).first()

        self.assertEqual(str(link1.organisation_id), str(self.id1))
        self.assertEqual(str(link2.organisation_id), str(self.id1))

        ancestors = s3db.pr_get_ancestors(branch1_pe_id)
        self.assertEqual(ancestors, [str(org1_pe_id)])

        ancestors = s3db.pr_get_ancestors(branch2_pe_id)
        self.assertEqual(ancestors, [str(org1_pe_id)])

    # -------------------------------------------------------------------------
    def testMergeVirtualReference(self):
        """ Test merge with virtual references """

        utable = current.auth.settings.table_user
        user = Storage(first_name="Test",
                       last_name="User",
                       password="xyz",
                       email="testuser@example.com",
                       organisation_id=self.id2)
        user_id = utable.insert(**user)

        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)

        user = current.db(utable.id == user_id).select(limitby=(0, 1)).first()
        self.assertNotEqual(user, None)

        self.assertEqual(str(user.organisation_id), str(self.id1))

    # -------------------------------------------------------------------------
    def testMergeRealms(self):
        """ Test merge of realms when merging two person entities """

        org1, org2 = self.get_records()

        s3db = current.s3db
        org1_pe_id = s3db.pr_get_pe_id(org1)
        org2_pe_id = s3db.pr_get_pe_id(org2)

        person = Storage(first_name="Nxthga",
                         realm_entity=org2_pe_id)
        ptable = s3db.pr_person
        person_id = ptable.insert(**person)

        person = ptable[person_id]
        self.assertEqual(person.realm_entity, org2_pe_id)

        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)

        person = ptable[person_id]
        self.assertEqual(person.realm_entity, org1_pe_id)

    # -------------------------------------------------------------------------
    def get_records(self):

        table = self.resource.table
        query = (table._id.belongs(self.id1, self.id2))
        rows = current.db(query).select(limitby=(0, 2))
        row1 = row2 = None
        for row in rows:
            row_id = row[table._id]
            if row_id == self.id1:
                row1 = row
            elif row_id == self.id2:
                row2 = row
        return (row1, row2)

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.db.rollback()
        current.auth.override = False

# =============================================================================
class MergePersonsTests(unittest.TestCase):
    """ Test merging pr_person records """

    # -------------------------------------------------------------------------
    def setUp(self):
        """ Set up person records """

        db = current.db
        auth = current.auth
        s3db = current.s3db
        deployment_settings = current.deployment_settings

        auth.override = True

        ptable = s3db.pr_person

        person1 = Storage(first_name="Test",
                          last_name="Person")
        person1_id = ptable.insert(**person1)
        person1.update(id=person1_id)
        s3db.update_super(ptable, person1)

        person2 = Storage(first_name="Test",
                          last_name="Person")
        person2_id = ptable.insert(**person2)
        person2.update(id=person2_id)
        s3db.update_super(ptable, person2)

        self.id1 = person1_id
        self.id2 = person2_id

        self.resource = s3db.resource("pr_person")

    # -------------------------------------------------------------------------
    def testPermissionError(self):
        """ Check for exception if not authorized """
        
        db = current.db
        auth = current.auth
        s3db = current.s3db
        deployment_settings = current.deployment_settings

        # Anonymous
        auth.override = False
        auth.s3_impersonate(None)

        self.assertRaises(current.auth.permission.error,
                          self.resource.merge, self.id1, self.id2)
                          
        # Check for proper rollback
        ptable = s3db.pr_person
        query = ptable._id.belongs((self.id1, self.id2))
        rows = db(query).select(ptable._id, limitby=(0, 2))
        self.assertEqual(len(rows), 0)

    # -------------------------------------------------------------------------
    def testOriginalNotFoundError(self):
        """ Check for exception if record not found """
        
        db = current.db
        s3db = current.s3db
        deployment_settings = current.deployment_settings

        self.assertRaises(KeyError, self.resource.merge, 0, self.id2)
        # Check for proper rollback
        ptable = s3db.pr_person
        query = ptable._id.belongs((self.id1, self.id2))
        rows = db(query).select(ptable._id, limitby=(0, 2))
        self.assertEqual(len(rows), 0)

    # -------------------------------------------------------------------------
    def testNotDuplicateFoundError(self):
        """ Check for exception if record not found """
        
        db = current.db
        s3db = current.s3db
        deployment_settings = current.deployment_settings

        self.assertRaises(KeyError, self.resource.merge, self.id1, 0)
        # Check for proper rollback
        ptable = s3db.pr_person
        query = ptable._id.belongs((self.id1, self.id2))
        rows = db(query).select(ptable._id, limitby=(0, 2))
        self.assertEqual(len(rows), 0)

    # -------------------------------------------------------------------------
    def testMerge(self):
        """ Test merge """

        # Merge records
        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)

        # Check the merged records
        person1, person2 = self.get_records()
        self.assertNotEqual(person1, None)
        self.assertNotEqual(person2, None)

        # Check deleted status
        self.assertFalse(person1.deleted)
        self.assertTrue(person2.deleted)
        self.assertEqual(str(self.id1), str(person2.deleted_rb))

        # Check values
        self.assertEqual(person1.first_name, "Test")
        self.assertEqual(person1.last_name, "Person")

        self.assertEqual(person2.first_name, "Test")
        self.assertEqual(person2.last_name, "Person")

    # -------------------------------------------------------------------------
    def testMergeWithUpdate(self):
        """ Test merge with update """

        success = self.resource.merge(self.id1, self.id2,
                                      update = Storage(first_name = "Changed"))
        self.assertTrue(success)
        person1, person2 = self.get_records()

        self.assertNotEqual(person1, None)
        self.assertNotEqual(person2, None)

        self.assertFalse(person1.deleted)
        self.assertTrue(person2.deleted)
        self.assertEqual(str(self.id1), str(person2.deleted_rb))

        self.assertEqual(person1.first_name, "Changed")
        self.assertEqual(person1.last_name, "Person")

        self.assertEqual(person2.first_name, "Test")
        self.assertEqual(person2.last_name, "Person")

    # -------------------------------------------------------------------------
    def testMergeSingleComponent(self):
        """ Test merge of single-component """

        db = current.db
        s3db = current.s3db
        deployment_settings = current.deployment_settings

        person1, person2 = self.get_records()

        dtable = s3db.pr_physical_description

        pd1 = Storage(pe_id=person1.pe_id,
                      blood_type="B+")
        pd1_id = dtable.insert(**pd1)
        pd1.update(id=pd1_id)
        s3db.update_super(dtable, pd1)

        pd2 = Storage(pe_id=person2.pe_id,
                      blood_type="B-")
        pd2_id = dtable.insert(**pd2)
        pd2.update(id=pd2_id)
        s3db.update_super(dtable, pd2)

        success = self.resource.merge(self.id1, self.id2,
                                      replace = ["physical_description.blood_type"])

        self.assertTrue(success)

        pd1 = db(dtable._id == pd1_id).select(limitby=(0, 1)).first()
        self.assertNotEqual(pd1, None)
        self.assertFalse(pd1.deleted)
        self.assertEqual(pd1.blood_type, "B-")
        self.assertEqual(pd1.pe_id, person1.pe_id)

        pd2 = db(dtable._id == pd2_id).select(limitby=(0, 1)).first()
        self.assertNotEqual(pd2, None)
        self.assertTrue(pd2.deleted)
        self.assertEqual(str(pd2.deleted_rb), str(pd1.id))

    # -------------------------------------------------------------------------
    def testMergeMultiComponent(self):
        """ Test merge of multiple-component """

        db = current.db
        s3db = current.s3db
        deployment_settings = current.deployment_settings

        person1, person2 = self.get_records()

        itable = s3db.pr_identity

        id1 = Storage(person_id=person1.id,
                      type=1,
                      value="TEST1")
        id1_id = itable.insert(**id1)
        id1.update(id=id1_id)
        s3db.update_super(itable, id1)

        id2 = Storage(person_id=person2.id,
                      type=1,
                      value="TEST2")
        id2_id = itable.insert(**id2)
        id2.update(id=id2_id)
        s3db.update_super(itable, id2)

        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)

        id1 = db(itable._id == id1_id).select(limitby=(0, 1)).first()
        self.assertNotEqual(id1, None)
        self.assertFalse(id1.deleted)
        self.assertEqual(id1.person_id, self.id1)

        id2 = db(itable._id == id2_id).select(limitby=(0, 1)).first()
        self.assertNotEqual(id2, None)
        self.assertFalse(id2.deleted)
        self.assertEqual(id2.person_id, self.id1)

    # -------------------------------------------------------------------------
    def get_records(self):

        db = current.db
        table = self.resource.table
        query = (table._id.belongs(self.id1, self.id2))
        rows = db(query).select(limitby=(0, 2))
        row1 = row2 = None
        for row in rows:
            row_id = row[table._id]
            if row_id == self.id1:
                row1 = row
            elif row_id == self.id2:
                row2 = row
        return (row1, row2)

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.db.rollback()
        current.auth.override = False

# =============================================================================
class MergeLocationsTests(unittest.TestCase):
    """ Test merging gis_locations """

    # -------------------------------------------------------------------------
    def setUp(self):
        """ Set up location records """

        auth = current.auth
        s3db = current.s3db

        auth.override = True

        ltable = s3db.gis_location

        location1 = Storage(name="TestLocation")
        location1_id = ltable.insert(**location1)

        location2 = Storage(name="TestLocation")
        location2_id = ltable.insert(**location2)

        self.id1 = location1_id
        self.id2 = location2_id

        self.resource = s3db.resource("gis_location")

    # -------------------------------------------------------------------------
    def testMerge(self):
        """ Test merge """

        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)
        location1, location2 = self.get_records()

        self.assertNotEqual(location1, None)
        self.assertNotEqual(location2, None)

        self.assertFalse(location1.deleted)
        self.assertTrue(location2.deleted)
        self.assertEqual(str(self.id1), str(location2.deleted_rb))

        self.assertEqual(location1.name, "TestLocation")
        self.assertEqual(location2.name, "TestLocation")

    # -------------------------------------------------------------------------
    def testMergeSimpleReference(self):
        """ Test merge of a simple reference including super-entity """

        db = current.db
        s3db = current.s3db

        # Create an office referencing location 2
        otable = s3db.org_office
        office = Storage(name="Test Office",
                         location_id = self.id2)
        office_id = otable.insert(**office)
        office.update(id=office_id)
        s3db.update_super(otable, office)

        # Merge location 2 into 1
        success = self.resource.merge(self.id1, self.id2)
        self.assertTrue(success)

        # Check the location_id in office is now location 1
        office = db(otable._id == office.id).select(limitby=(0, 1)).first()
        self.assertNotEqual(office, None)
        self.assertEqual(office.location_id, self.id1)

        # Check the location_id in the org_site super record is also location 1
        stable = s3db.org_site
        site = db(stable.site_id == office.site_id).select(limitby=(0, 1)).first()
        self.assertNotEqual(site, None)
        self.assertEqual(site.location_id, self.id1)

    # -------------------------------------------------------------------------
    #def testMergeLocationHierarchy(self):
        #""" Test update of the location hierarchy when merging locations """
        #pass

    # -------------------------------------------------------------------------
    #def testMergeDeduplicateComponents(self):
        #""" Test merged components deduplication """
        ## Test by gis_location_tags
        #pass

    # -------------------------------------------------------------------------
    def get_records(self):

        table = self.resource.table
        query = (table._id.belongs(self.id1, self.id2))
        rows = current.db(query).select(limitby=(0, 2))
        row1 = row2 = None
        for row in rows:
            row_id = row[table._id]
            if row_id == self.id1:
                row1 = row
            elif row_id == self.id2:
                row2 = row
        return (row1, row2)

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.db.rollback()
        current.auth.override = False

# =============================================================================
class MergeReferenceListsTest(unittest.TestCase):

    # -------------------------------------------------------------------------
    def setUp(self):
        
        tablename = self.tablename = "merge_list_reference"
        db = current.db
        db.define_table(tablename,
                        Field("facility_type_id",
                              "list:reference org_facility_type"),
                        *s3_meta_fields())
                                
        xmlstr = """
<s3xml>
    <resource name="org_facility_type" uuid="TESTMERGEFACTYPE1">
        <data field="name">TestMergeFacilityType1</data>
    </resource>
    <resource name="org_facility_type" uuid="TESTMERGEFACTYPE2">
        <data field="name">TestMergeFacilityType2</data>
    </resource>
    <resource name="%(tablename)s" uuid="TESTMERGEFACILITY">
        <reference field="facility_type_id" resource="org_facility_type"
                   uuid="[&quot;TESTMERGEFACTYPE1&quot;, &quot;TESTMERGEFACTYPE2&quot;]"/>
    </resource>
</s3xml>""" % dict(tablename=tablename)

        current.auth.override = True
        xmltree = etree.ElementTree(etree.fromstring(xmlstr))
        resource = current.s3db.resource(tablename)
        resource.import_xml(xmltree)

    # -------------------------------------------------------------------------
    def testMergeListReference(self):

        s3db = current.s3db
    
        resource = s3db.resource("org_facility_type",
                                 uid=["TESTMERGEFACTYPE1", "TESTMERGEFACTYPE2"])

        rows = resource.select(["id"], limit=2, as_rows=True)
        self.assertEqual(len(rows), 2)
        
        original = rows[0].id
        duplicate = rows[1].id
        resource.merge(original, duplicate)

        resource = s3db.resource(self.tablename,
                                 uid="TESTMERGEFACILITY")
        rows = resource.select(["id", "facility_type_id"],
                               limit=None, as_rows=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].facility_type_id, [original])

    # -------------------------------------------------------------------------
    def tearDown(self):

        db = current.db
        db.rollback()
        try:
            db[self.tablename].drop()
        except:
            pass
        current.auth.override = False

# =============================================================================
class ResourceGetTests(unittest.TestCase):
    """ Test S3Resource.get """

    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):

        current.auth.override = True

        xmlstr = """
<s3xml>
    <resource name="org_organisation" uuid="GETTESTORG">
        <data field="name">GetTestOrg</data>
        <resource name="org_office" uuid="GETTESTOFFICE">
            <data field="name">GetTestOffice</data>
        </resource>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))
        resource = current.s3db.resource("org_organisation")
        resource.import_xml(xmltree)

    # -------------------------------------------------------------------------
    def setUp(self):

        otable = current.s3db.org_organisation
        row = current.db(otable.uuid == "GETTESTORG") \
                     .select(otable.id, limitby=(0, 1)).first()
        self.org_id = row.id

    # -------------------------------------------------------------------------
    def testGetError(self):
        """ get() without ID raises a KeyError """

        resource = current.s3db.resource("org_organisation",
                                         uid="GETTESTORG")
        self.assertRaises(KeyError, resource.get, None)

    # -------------------------------------------------------------------------
    def testGetMaster(self):
        """ get() with an ID returns the record, if accessible """

        resource = current.s3db.resource("org_organisation",
                                         uid="GETTESTORG")
        record = resource.get(self.org_id)
        self.assertNotEqual(record, None)

        self.assertTrue(isinstance(record, Row))
        self.assertEqual(record.id, self.org_id)
        self.assertEqual(record.uuid, "GETTESTORG")
        self.assertEqual(record.name, "GetTestOrg")

    # -------------------------------------------------------------------------
    def testGetMasterFail(self):
        """ get() with an ID raises a KeyError, if not accessible """

        resource = current.s3db.resource("org_organisation",
                                         uid="OTHERTESTORG")
        self.assertRaises(KeyError, resource.get, self.org_id)

    # -------------------------------------------------------------------------
    def testGetComponent(self):
        """ get() with ID and component alias returns the components records """

        resource = current.s3db.resource("org_organisation",
                                         uid="GETTESTORG")
        records = resource.get(self.org_id, "office")
        self.assertNotEqual(records, None)

        self.assertTrue(len(records), 1)
        record = records[0]
        self.assertTrue(isinstance(record, Row))
        self.assertEqual(record.organisation_id, self.org_id)
        self.assertEqual(record.uuid, "GETTESTOFFICE")
        self.assertEqual(record.name, "GetTestOffice")

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):

        current.db.rollback()
        current.auth.override = False

# =============================================================================
class ResourceLazyVirtualFieldsSupportTests(unittest.TestCase):
    """ Test support for lazy virtual fields """

    # -------------------------------------------------------------------------
    def setUp(self):

        current.auth.override = True
        s3db = current.s3db
        table = s3db.pr_person
        if not hasattr(table, "name"):
            table.name = Field.Method("name", self.lazy_name)
            s3db.configure("pr_person",
                           extra_fields=["first_name", "last_name"])
        self.record_id = None

    # -------------------------------------------------------------------------
    def lazy_name(self, row):
        """ Dummy lazy field """

        self.record_id = row.pr_person.id
        return "%s %s" % (row.pr_person.first_name,
                          row.pr_person.last_name)

    # -------------------------------------------------------------------------
    def testLazyVirtualFieldsResolve(self):
        """
            Test whether field selectors for lazy virtual fields
            can be properly resolved
        """

        resource = current.s3db.resource("pr_person")

        from s3.s3resource import S3ResourceField
        rfield = S3ResourceField(resource, "name")
        self.assertEqual(rfield.field, None)
        self.assertEqual(rfield.ftype, "virtual")

    # -------------------------------------------------------------------------
    def testLazyVirtualFieldsExtract(self):
        """
            Test whether values for lazy virtual fields can be extracted
        """

        self.record_id = None

        resource = current.s3db.resource("pr_person")

        # Select raw rows
        rows = resource.select(["name", "first_name", "last_name"],
                               limit=1, as_rows=True)
        row = rows[0]
        self.assertTrue("name" in row)
        self.assertTrue(callable(row["name"]))
        # lazy field not called
        self.assertEqual(self.record_id, None)

        name = "%s %s" % (row.first_name, row.last_name)

        # Select with value extraction
        data = resource.select(["name"], limit=1)
        item = data["rows"][0]
        self.assertTrue("pr_person.name" in item)
        # lazy field called
        self.assertEqual(self.record_id, row.id)

        self.assertEqual(item["pr_person.name"], name)

    # -------------------------------------------------------------------------
    def testLazyVirtualFieldsFilter(self):
        """
            Test whether S3ResourceQueries work with lazy virtual fields
        """

        resource = current.s3db.resource("pr_person")

        from s3.s3resource import S3FieldSelector as FS
        query = FS("name").like("Admin%")
        resource.add_filter(query)

        data = resource.select(["name", "first_name", "last_name"],
                               limit=None)
        rows = data["rows"]
        for item in rows:
            self.assertTrue("pr_person.name" in item)
            self.assertEqual(item["pr_person.name"][:5], "Admin")
            self.assertEqual(item["pr_person.name"], "%s %s" % (
                             item["pr_person.first_name"],
                             item["pr_person.last_name"]))

    # -------------------------------------------------------------------------
    def testLazyVirtualFieldsURLFilter(self):
        """
            Test whether URL filters work with lazy virtual fields
        """

        vars = Storage({"person.name__like": "Admin*"})
        resource = current.s3db.resource("pr_person", vars=vars)

        data = resource.select(["name", "first_name", "last_name"],
                               limit=None)
        rows = data["rows"]
        for item in rows:
            self.assertTrue("pr_person.name" in item)
            self.assertEqual(item["pr_person.name"][:5], "Admin")
            self.assertEqual(item["pr_person.name"], "%s %s" % (
                             item["pr_person.first_name"],
                             item["pr_person.last_name"]))

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.auth.override = False

# =============================================================================
class URLQueryParserTests(unittest.TestCase):

    # -------------------------------------------------------------------------
    def setUp(self):

        current.auth.override = True

    # -------------------------------------------------------------------------
    def testParseExpression(self):
        """ Test URL Expression parsing """

        parse = S3URLQuery.parse_expression

        items = [
            # Correct syntax
            ("s", ["s"], "eq", False),
            ("s!", ["s"], "eq", True),
            ("s__op", ["s"], "op", False),
            ("s__op!", ["s"], "op", True),
            ("s1|s2|s3", ["s1", "s2", "s3"], "eq", False),
            ("s1|s2|s3!", ["s1", "s2", "s3"], "eq", True),
            ("s1|s2|s3__op", ["s1", "s2", "s3"], "op", False),
            ("s1|s2|s3__op!", ["s1", "s2", "s3"], "op", True),
            # Incorrect syntax
            ("s__", ["s"], "eq", False),
            ("s___", ["s"], "eq", False),
            ("s_____ne", ["s"], "ne", False),
            ("s__!", ["s"], "eq", True),
            ("s!__op", ["s!"], "op", False),
            ("s__!op", ["s"], "!op", False),
            ("s1||s3", ["s1", "s3"], "eq", False),
            ("s1|s2|s3__", ["s1", "s2", "s3"], "eq", False),
            ("s1|s2|s3__!", ["s1", "s2", "s3"], "eq", True),
            ("s1|s2|s3!__op", ["s1", "s2", "s3!"], "op", False),
            ("s1|s2|s3__!op", ["s1", "s2", "s3"], "!op", False),
        ]

        for key, selectors, op, invert in items:
            s, o, i = parse(key)
            self.assertEqual((key, s, o, i), (key, selectors, op, invert))

    # -------------------------------------------------------------------------
    def testParseValue(self):
        """ Test URL value parsing """

        parse = S3URLQuery.parse_value

        items = [
            ("123", "123"),
            ("1,2,3", ["1", "2", "3"]),
            ('"1,2",3', ["1,2", "3"]),
            (["1,2", "3"], ["1", "2", "3"]),
            ("NONE", None),
            ('"NONE"', "NONE"),
            ("None", None),
            ('"None"', "None"),
            ("NONE,1", [None, "1"]),
            ('"NONE",1', ["NONE", "1"]),
            ('"NONE,1"', "NONE,1"),
            ('"NONE",NONE,1,"Test\\""', ['NONE', None, "1", 'Test"']),
            (['"NONE",NONE,1','"Test\\"",None'], ['NONE', None, "1", 'Test"', None])
        ]
        for v, r in items:
            self.assertEqual((v, parse(v)), (v, r))

    # -------------------------------------------------------------------------
    def testParseURL(self):
        """ Test URL get_vars parsing """

        parse = S3URLQuery.parse_url

        items = [
            (None, Storage()),
            ("", Storage()),
            ("test", Storage()),
            ("x/y/z?", Storage()),
            ("x/z/z?a=b", Storage(a="b")),
            ("?a=b", Storage(a="b")),
            ("a=b", Storage(a="b")),
            ("a=b&a=c", Storage(a=["b", "c"])),
            ("a=b,c&a=d", Storage(a=["b,c", "d"])),
        ]
        for v, r in items:
            self.assertEqual((v, parse(v)), (v, r))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testParseURLQuery(self):
        """ Test standard URL query parsing """

        s3db = current.s3db

        project_project = s3db.project_project
        org_organisation = s3db.org_organisation
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        url_query = {"project.organisation_id$name__like": "*test*",
                     "task.description__like!": "*test*"}

        resource = current.s3db.resource("project_project", vars=url_query)
        rfilter = resource.rfilter

        # Check joins
        joins = rfilter.get_left_joins()
        self.assertNotEqual(joins, None)
        self.assertTrue(isinstance(joins, list))
        
        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)
        self.assertEqual(joins[0], str(expected))
                                   
        expected_l = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))
        expected_r = project_task.on(
                        project_task_project.task_id == project_task.id)
        self.assertEqual(joins[1], str(expected_l))
        self.assertEqual(joins[2], str(expected_r))

        # Check query
        query = rfilter.get_query()
        expected = (((project_project.deleted != True) &
                     (project_project.id > 0)) &
                    ((org_organisation.name.lower().like("%test%")) &
                    (~(project_task.description.lower().like("%test%")))))
                    
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testParseURLQueryWithAlternativeValues(self):
        """ Test URL query parsing with alternative values (OR) """

        s3db = current.s3db

        project_project = s3db.project_project
        org_organisation = s3db.org_organisation
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        url_query = {"project.organisation_id$name__like": "Test*,Other*"}

        resource = current.s3db.resource("project_project", vars=url_query)
        rfilter = resource.rfilter

        # Check joins
        joins = rfilter.get_left_joins()
        self.assertTrue(isinstance(joins, list))
        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)
        self.assertEqual(joins[0], str(expected))

        # Check query
        query = rfilter.get_query()
        expected = (((project_project.deleted != True) &
                     (project_project.id > 0)) &
                    ((org_organisation.name.lower().like("test%")) |
                     (org_organisation.name.lower().like("other%"))))
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testParseURLQueryWithMultipleValues(self):
        """ Test URL query parsing with multiple values (AND) """

        s3db = current.s3db

        project_project = s3db.project_project
        org_organisation = s3db.org_organisation
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        url_query = {"project.organisation_id$name__like": ["Test*", "Other*"]}

        resource = current.s3db.resource("project_project", vars=url_query)
        rfilter = resource.rfilter

        # Check joins
        joins = rfilter.get_left_joins()
        self.assertTrue(isinstance(joins, list))
        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)
        self.assertEqual(joins[0], str(expected))

        # Check query
        query = rfilter.get_query()
        expected = (((project_project.deleted != True) &
                     (project_project.id > 0)) &
                    ((org_organisation.name.lower().like("other%")) &
                     (org_organisation.name.lower().like("test%"))))
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("project"), "project module disabled")
    def testParseURLQueryWithAlternativeSelectors(self):
        """ Test alternative selectors (OR) in a URL query """

        s3db = current.s3db

        project_project = s3db.project_project
        org_organisation = s3db.org_organisation
        project_task_project = s3db.project_task_project
        project_task = s3db.project_task

        url_query = {"project.organisation_id$name|task.description__like": "Test*"}

        resource = s3db.resource("project_project", vars=url_query)
        rfilter = resource.rfilter

        # Check joins
        joins = rfilter.get_left_joins()
        self.assertTrue(isinstance(joins, list))

        expected = org_organisation.on(
                        project_project.organisation_id == org_organisation.id)
        self.assertEqual(joins[0], str(expected))
        
        expected_l = project_task_project.on(
                        (project_task_project.project_id == project_project.id) &
                        (project_task_project.deleted != True))
        expected_r = project_task.on(
                        project_task_project.task_id == project_task.id)
        self.assertEqual(joins[1], str(expected_l))
        self.assertEqual(joins[2], str(expected_r))

        # Check the query
        query = rfilter.get_query()
        expected = (((project_project.deleted != True) &
                     (project_project.id > 0)) &
                    ((org_organisation.name.lower().like("test%")) |
                     (project_task.description.lower().like("test%"))))
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    def testBBOXFilter(self):
        """ Test URL query with BBOX filter """

        s3db = current.s3db

        org_office = s3db.org_office
        gis_location = s3db.gis_location

        url_query = {"bbox": "119.80485082193,12.860457717185,122.27677462907,15.107136411359"}

        resource = s3db.resource("org_office", vars=url_query)
        rfilter = resource.rfilter

        # Check the query
        query = rfilter.get_query()
        expected = (((org_office.deleted != True) &
                     (org_office.id > 0)) &
                    ((org_office.location_id == gis_location.id) &
                     ((((gis_location.lon > 119.80485082193) &
                        (gis_location.lon < 122.27677462907)) &
                       (gis_location.lat > 12.860457717185)) &
                      (gis_location.lat < 15.107136411359))))
                                     
        self.assertEqual(str(query), str(expected))

    # -------------------------------------------------------------------------
    def tearDown(self):

        current.auth.override = False

# =============================================================================
class ResourceFilteredComponentTests(unittest.TestCase):
    """ Test components from the same table but different aliases """

    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testAttachFilteredComponent(self):
        """ Test instantiation of filtered component """

        s3db = current.s3db

        # Define a filtered component with single value
        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": 5,
                                         },
                           )

        # Define the resource
        resource = s3db.resource("org_organisation", components=["test"])

        # Check the component
        component = resource.components["test"]
        table = component.table
        self.assertEqual(component.tablename, "org_office")
        self.assertEqual(component._alias, "org_test_office")
        self.assertEqual(table._tablename, "org_test_office")
        self.assertEqual(str(component.filter),
                         str((table.office_type_id == 5)))

        # Define a filtered component with single value in list
        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": [5],
                                         },
                           )
        resource = s3db.resource("org_organisation", components=["test"])
        component = resource.components["test"]
        table = component.table
        self.assertEqual(str(component.filter),
                         str((table.office_type_id == 5)))

        # Define a filtered component with value list
        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": [4, 5],
                                         },
                           )
        resource = s3db.resource("org_organisation", components=["test"])
        component = resource.components["test"]
        table = component.table
        self.assertEqual(str(component.filter),
                         str((table.office_type_id.belongs(4,5))))

        # Define a filtered component with empty filter value list
        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": [],
                                         },
                           )
        resource = s3db.resource("org_organisation", components=["test"])
        component = resource.components["test"]
        self.assertEqual(component.filter, None)

        # Remove the component hook
        del current.model.components["org_organisation"]["test"]

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testResolveSelectorWithFilteredComponent(self):
        """ Test resolution of field selectors for filtered components """

        s3db = current.s3db

        # Define a filtered component
        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": 5,
                                         },
                           )

        # Define the resource
        resource = s3db.resource("org_organisation")

        # Make sure an S3ResourceField of the component is using the
        # correct table alias (critical for data extraction from Rows)
        rfield = S3ResourceField(resource, "test.name")
        self.assertEqual(rfield.tname, "org_test_office")
        self.assertEqual(rfield.colname, "org_test_office.name")

        # Remove the component hook
        del current.model.components["org_organisation"]["test"]

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testURLQueryWithFilteredComponent(self):
        """ Test resolution of URL queries for fields in filtered components """

        auth = current.auth
        s3db = current.s3db
        
        org_organisation = s3db.org_organisation
        org_test_office = s3db.org_office.with_alias("org_test_office")

        # Define a filtered component
        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": 5,
                                         },
                           )

        # Define the resource
        resource = s3db.resource("org_organisation")

        # Translate a URL query into a DAL query, check that
        # the correct table alias is used
        query = S3URLQuery.parse(resource, {"test.name__like": "xyz*"})
        self.assertEqual(str(query.test[0].query(resource)),
                         str(org_test_office.name.lower().like("xyz%")))

        # Add the query to the resource
        auth.override = True
        resource.add_filter(query.test[0])
        rfilter = resource.rfilter

        # Check that the aliased table is properly joined
        expected = org_test_office.on(
                        ((org_test_office.organisation_id == org_organisation.id) &
                         (org_test_office.deleted != True)) &
                        (org_test_office.office_type_id == 5))
        self.assertEqual(str(rfilter.get_left_joins()[0]), str(expected))
        
        # ...and the effective query of the master contains the filter
        # and is using the correct alias
        expected = (((org_organisation.deleted != True) &
                     (org_organisation.id > 0)) &
                    (org_test_office.name.lower().like("xyz%")))
        self.assertEqual(str(resource.get_query()), str(expected))

        # Check the query of the component
        expected = ((((org_test_office.deleted != True) &
                    (org_test_office.id > 0)) &
                    (((org_organisation.deleted != True) &
                    (org_organisation.id > 0)) &
                    (org_test_office.name.lower().like("xyz%")))) &
                    (((org_test_office.organisation_id == org_organisation.id) &
                    (org_test_office.deleted != True)) &
                    (org_test_office.office_type_id == 5)))
        self.assertEqual(str(resource.components["test"].get_query()),
                         str(expected))
        
        # Remove the component hook
        del current.model.components["org_organisation"]["test"]

        auth.override = False

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testDataTableFilterWithFilteredComponent(self):
        """
            Test translation of datatable filter/sorting for fields in
            filtered components
        """
        
        s3db = current.s3db

        org_organisation = s3db.org_organisation
        org_office_type = s3db.org_office_type
        org_test_office = s3db.org_office.with_alias("org_test_office")

        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": 5,
                                         },
                           )

        resource = s3db.resource("org_organisation")
        fields = ["id", "name", "test.name", "test.office_type_id$name"]
        vars = Storage({"bSortable_0": "false", # action column
                        "bSortable_1": "true",
                        "bSortable_2": "true",
                        "bSortable_3": "true",
                        "sSortDir_0": "asc",
                        "iSortCol_0": "2",
                        "sSortDir_1": "desc",
                        "iSortCol_1": "3",
                        "iColumns": "4",
                        "iSortingCols": "2",
                        "sSearch": "test"})
        searchq, orderby, left = resource.datatable_filter(fields, vars)
        expected = (((org_organisation.name.lower().like("%test%")) |
                     (org_test_office.name.lower().like("%test%"))) |
                    (org_office_type.name.lower().like("%test%")))
        self.assertEqual(str(searchq), str(expected))
        self.assertEqual(orderby,
                         "org_test_office.name asc, "
                         "org_office_type.name desc")
        
        # Remove the component hook
        del current.model.components["org_organisation"]["test"]

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testSelectWithFilteredComponent(self):
        """ Test S3Resource.select with fields in a filtered component """
    
        s3db = current.s3db
        auth = current.auth
        
        xmlstr = """
<s3xml>
    <resource name="org_organisation" uuid="FCTESTORG">
        <data field="name">FilteredComponentsTestOrg</data>
        <resource name="org_office" uuid="FCTESTOFFICE">
            <data field="name">FilteredComponentsTestOffice</data>
            <reference field="office_type_id" resource="org_office_type">
                <resource name="org_office_type" uuid="FCTESTTYPE">
                    <data field="name">FilteredComponentsTestType</data>
                </resource>
            </reference>
        </resource>
    </resource>
</s3xml>"""

        xmltree = etree.ElementTree(etree.fromstring(xmlstr))

        auth.override = True
        
        resource = s3db.resource("org_organisation")
        resource.import_xml(xmltree)

        resource = s3db.resource("org_office_type", uid="FCTESTTYPE")
        row = resource.select(["id"], limit=1, as_rows=True)[0]
        type_id = row.id

        s3db.add_components("org_organisation",
                            org_office = {"name": "test",
                                          "joinby": "organisation_id",
                                          "filterby": "office_type_id",
                                          "filterfor": type_id,
                                         },
                           )
        
        resource = current.s3db.resource("org_organisation", uid="FCTESTORG")
        fields = ["id", "name", "test.name", "test.office_type_id$name"]
        data = resource.select(fields, limit=None)
        result = data["rows"]

        self.assertEqual(len(result), 1)
        result = result[0]
        self.assertTrue("org_organisation.name" in result)
        self.assertEqual(result["org_organisation.name"], "FilteredComponentsTestOrg")
        self.assertTrue("org_test_office.name" in result)
        self.assertEqual(result["org_test_office.name"], "FilteredComponentsTestOffice")
        self.assertTrue("org_office_type.name" in result)
        self.assertEqual(result["org_office_type.name"], "FilteredComponentsTestType")

        # Remove the component hook
        del current.model.components["org_organisation"]["test"]

        current.db.rollback()
        auth.override = False

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("hrm"), "hrm module disabled")
    def testGetJoinLinkTableComponentAlias(self):
        """ Join for a link-table component with alias """

        s3db = current.s3db

        hrm_human_resource = s3db.hrm_human_resource
        pr_person = s3db.pr_person
        pr_email_contact = s3db.pr_contact.with_alias("pr_email_contact")
        pr_phone_contact = s3db.pr_contact.with_alias("pr_phone_contact")

        resource = current.s3db.resource("hrm_human_resource")

        component = resource.components["email"]
        join = component.get_join()
        expected = (((pr_person.deleted != True) &
                    ((hrm_human_resource.person_id == pr_person.id) &
                    (pr_person.pe_id == pr_email_contact.pe_id))) &
                    (pr_email_contact.contact_method == "EMAIL"))
        self.assertEqual(str(join), str(expected))

        component = resource.components["phone"]
        join = component.get_join()
        expected = (((pr_person.deleted != True) &
                    ((hrm_human_resource.person_id == pr_person.id) &
                    (pr_person.pe_id == pr_phone_contact.pe_id))) &
                    (pr_phone_contact.contact_method == "SMS"))
        self.assertEqual(str(join), str(expected))

    # -------------------------------------------------------------------------
    @unittest.skipIf(not current.deployment_settings.has_module("hrm"), "hrm module disabled")
    def testGetLeftJoinLinkTableComponentAlias(self):
        """ Left Join for a link-table component with alias """

        s3db = current.s3db
        resource = s3db.resource("hrm_human_resource")
        
        pr_person = s3db.pr_person
        hrm_human_resource = s3db.hrm_human_resource
        pr_contact = s3db.pr_contact

        component = resource.components["email"]
        pr_email_contact = pr_contact.with_alias("pr_email_contact")
        ljoin = component.get_left_join()
        
        self.assertTrue(isinstance(ljoin, list))
        self.assertEqual(len(ljoin), 2)
        self.assertEqual(str(ljoin[0]), str(pr_person.on(
                            (hrm_human_resource.person_id == pr_person.id) &
                            (pr_person.deleted != True))))
                            
        self.assertEqual(str(ljoin[1]), str(pr_email_contact.on(
                                (pr_person.pe_id == pr_email_contact.pe_id) &
                                (pr_email_contact.contact_method == "EMAIL"))))

        component = resource.components["phone"]
        pr_phone_contact = pr_contact.with_alias("pr_phone_contact")
        ljoin = component.get_left_join()
        
        self.assertTrue(isinstance(ljoin, list))
        self.assertEqual(len(ljoin), 2)
        self.assertEqual(str(ljoin[0]), str(pr_person.on(
                            (hrm_human_resource.person_id == pr_person.id) &
                            (pr_person.deleted != True))))
                                        
        self.assertEqual(str(ljoin[1]), str(pr_phone_contact.on(
                                (pr_person.pe_id == pr_phone_contact.pe_id) &
                                (pr_phone_contact.contact_method == "SMS"))))

    # -------------------------------------------------------------------------
    # Disabled - @todo: must create test records (otherwise component can be
    # empty regardless) - and check the actual office_type_ids (can not assume 4/5)
    @unittest.skip("disabled until fixed")
    @unittest.skipIf(not current.deployment_settings.has_module("org"), "org module disabled")
    def testExportTreeWithComponentAlias(self):
        """ Test export of a resource that has components from the same table but different aliases """

        current.auth.override = True
        s3db = current.s3db
        s3db.add_components("org_organisation",
                            org_office = ({"name": "fieldoffice",
                                           "joinby": "organisation_id",
                                           "filterby": "office_type_id",
                                           "filterfor": 5,
                                          },
                                          {"name": "hq",
                                           "joinby": "organisation_id",
                                           "filterby": "office_type_id",
                                           "filterfor": 4,
                                          },
                                         ),
                           )
                           
        resource = s3db.resource("org_organisation")
        self.assertEqual(str(resource.components.fieldoffice.filter), \
                         "(org_fieldoffice_office.office_type_id = 5)")
        self.assertEqual(str(resource.components.hq.filter), \
                         "(org_hq_office.office_type_id = 4)")
        
        tree = resource.export_tree(mcomponents=["fieldoffice","hq"])
        self.assertTrue(resource.components.fieldoffice._length > 0)
        self.assertTrue(resource.components.hq._length > 0)
        self.assertTrue(resource.components.office._length is None)
        
        tree = resource.export_tree(mcomponents=["org_office","fieldoffice","hq"])
        self.assertTrue(resource.components.office._length > 0)
        self.assertTrue(resource.components.fieldoffice._length is None)
        self.assertTrue(resource.components.hq._length is None)

# =============================================================================
class ResourceDeleteTests(unittest.TestCase):

    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):

        s3db = current.s3db

        # Create super-entity
        s3db.super_entity("del_super",
                          "del_super_id",
                          {"del_master": "DEL Master"})

        # Define master table
        s3db.define_table("del_master",
                          s3db.super_link("del_super_id",
                                          "del_super"),
                          *s3_meta_fields())

        current.db.commit()

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):

        # Drop test tables
        db = current.db
        db.del_master.drop()
        db.del_super.drop()

        current.db.commit()

    # -------------------------------------------------------------------------
    def setUp(self):

        s3db = current.s3db

        # Make master instance type of super
        s3db.configure("del_master", super_entity = "del_super")

        # Create the master record and link it to the SE
        master_table = s3db.del_master
        master_id = master_table.insert()
        s3db.update_super(master_table, {"id": master_id})
        self.master_id = master_id

        self.master_deleted = 0
        self.super_deleted = 0
        self.component_deleted = 0

        # Configure callbacks
        s3db.configure("del_master",
                       ondelete = self.master_ondelete)

        s3db.configure("del_super",
                       ondelete = self.super_ondelete)

        s3db.configure("del_component",
                       ondelete = self.component_ondelete)

        current.db.commit()
        current.auth.override = True

    # -------------------------------------------------------------------------
    def tearDown(self):

        # Remove test records
        db = current.db
        db(db.del_master._id>0).delete()
        db(db.del_super._id>0).delete()
        db.commit()
        
        current.auth.override = False

    # -------------------------------------------------------------------------
    def master_ondelete(self, row):
        """ Dummy ondelete-callback """

        self.master_deleted = row.id
        return
        
    # -------------------------------------------------------------------------
    def super_ondelete(self, row):
        """ Dummy ondelete-callback """

        self.super_deleted = row.id
        return

    # -------------------------------------------------------------------------
    def component_ondelete(self, row):
        """ Dummy ondelete-callback """

        self.component_deleted = row.id
        return

    # -------------------------------------------------------------------------
    def testArchiveSimple(self):
        """ Test archiving of a record """

        s3db = current.s3db
        s3db.clear_config("del_master", "super_entity")
        
        master_id = self.master_id

        # Delete the master record
        resource = s3db.resource("del_master", id=master_id)
        success = resource.delete()
        self.assertEqual(success, 1)
        self.assertEqual(resource.error, None)

        # Master record is deleted
        table = s3db.del_master
        record = table[master_id]
        self.assertTrue(record.deleted)

        # Check callbacks
        self.assertEqual(self.master_deleted, master_id)
        self.assertEqual(self.super_deleted, 0)
        self.assertEqual(self.component_deleted, 0)

    # -------------------------------------------------------------------------
    def testArchiveCascade(self):
        """
            Test archiving of a record which is referenced by
            other records
        """

        s3db = current.s3db
        s3db.clear_config("del_master", "super_entity")

        master_id = self.master_id

        # Define component table
        s3db.define_table("del_component",
                          Field("del_master_id",
                                s3db.del_master,
                                ondelete="CASCADE"),
                          *s3_meta_fields())
        component = s3db["del_component"]
        s3db.add_components("del_master",
                            del_component="del_master_id")

        try:
            # Create a component record
            component_id = component.insert(del_master_id=master_id)
            component_record = component[component_id]
            self.assertNotEqual(component_record, None)
            current.db.commit()

            # Delete the master record
            resource = s3db.resource("del_master", id=master_id)
            success = resource.delete()
            self.assertEqual(success, 1)
            self.assertEqual(resource.error, None)

            # Master record is deleted
            table = s3db.del_master
            record = table[master_id]
            self.assertTrue(record.deleted)

            # Component record is deleted and unlinked
            component_record = component[component_id]
            self.assertTrue(component_record.deleted)
            self.assertEqual(component_record.del_master_id, None)

            # Check callbacks
            self.assertEqual(self.master_deleted, master_id)
            self.assertEqual(self.super_deleted, 0)
            self.assertEqual(self.component_deleted, component_id)

        finally:
            component.drop()
            del current.model.components["del_master"]["component"]

    # -------------------------------------------------------------------------
    def testArchiveSetNull(self):
        """
            Test archiving of a record which is referenced by
            other records
        """

        s3db = current.s3db
        s3db.clear_config("del_master", "super_entity")

        master_id = self.master_id

        # Define component table
        s3db.define_table("del_component",
                          Field("del_master_id",
                                s3db.del_master,
                                ondelete="SET NULL"),
                          *s3_meta_fields())
        component = s3db["del_component"]
        s3db.add_components("del_master",
                            del_component="del_master_id")

        try:
            # Create a component record
            component_id = component.insert(del_master_id=master_id)
            component_record = component[component_id]
            self.assertNotEqual(component_record, None)
            current.db.commit()

            # Delete the master record
            resource = s3db.resource("del_master", id=master_id)
            success = resource.delete()
            self.assertEqual(success, 1)
            self.assertEqual(resource.error, None)

            # Master record is deleted
            table = s3db.del_master
            record = table[master_id]
            self.assertTrue(record.deleted)

            # Component record is not deleted, but unlinked
            component_record = component[component_id]
            self.assertFalse(component_record.deleted)
            self.assertEqual(component_record.del_master_id, None)
            
            # Check callbacks
            self.assertEqual(self.master_deleted, master_id)
            self.assertEqual(self.super_deleted, 0)
            self.assertEqual(self.component_deleted, 0)

        finally:
            component.drop()
            del current.model.components["del_master"]["component"]

    # -------------------------------------------------------------------------
    def testArchiveRestrict(self):
        """
            Test archiving of a record which is referenced by
            other records
        """


        s3db = current.s3db
        s3db.clear_config("del_master", "super_entity")

        master_id = self.master_id

        # Define component table
        s3db.define_table("del_component",
                          Field("del_master_id",
                                s3db.del_master,
                                ondelete="RESTRICT"),
                          *s3_meta_fields())
        component = s3db["del_component"]
        s3db.add_components("del_master",
                            del_component="del_master_id")

        try:
            # Create a component record
            component_id = component.insert(del_master_id=master_id)
            component_record = component[component_id]
            self.assertNotEqual(component_record, None)
            current.db.commit()

            # Delete the master record
            resource = s3db.resource("del_master", id=master_id)
            success = resource.delete()
            self.assertEqual(success, 0)
            self.assertEqual(resource.error, current.ERROR.INTEGRITY_ERROR)

            # Master record is not deleted
            table = s3db.del_master
            record = table[master_id]
            self.assertFalse(record.deleted)

            # Component record is not deleted and still linked
            component_record = component[component_id]
            self.assertFalse(component_record.deleted)
            self.assertEqual(component_record.del_master_id, master_id)

            # Check callbacks
            self.assertEqual(self.master_deleted, 0)
            self.assertEqual(self.super_deleted, 0)
            self.assertEqual(self.component_deleted, 0)

        finally:
            component.drop()
            del current.model.components["del_master"]["component"]
            
    # -------------------------------------------------------------------------
    def testArchiveSuper(self):
        """
            Test archiving of a super-entity instance record
        """

        s3db = current.s3db

        master_id = self.master_id

        # Get the super_id
        table = s3db.del_master
        record = table[master_id]
        super_id = record["del_super_id"]

        # Delete the master record
        resource = s3db.resource("del_master", id=master_id)
        success = resource.delete()
        self.assertEqual(success, 1)
        self.assertEqual(resource.error, None)

        # Master record is deleted
        record = table[master_id]
        self.assertTrue(record.deleted)
        self.assertEqual(record.del_super_id, None)

        # Super-record is deleted
        stable = s3db.del_super
        srecord = stable[super_id]
        self.assertTrue(srecord.deleted)

        # Check callbacks
        self.assertEqual(self.master_deleted, master_id)
        self.assertEqual(self.super_deleted, super_id)
        self.assertEqual(self.component_deleted, 0)

    # -------------------------------------------------------------------------
    def testArchiveSuperCascade(self):
        """
            Test archiving of a super-entity instance record
            where the super-record is referenced by other records
            with CASCADE constraint
        """

        s3db = current.s3db

        master_id = self.master_id

        # Define component table
        s3db.define_table("del_component",
                          s3db.super_link("del_super_id",
                                          "del_super",
                                          ondelete="CASCADE"),
                          *s3_meta_fields())
        component = s3db["del_component"]
        s3db.add_components("del_super",
                            del_component="del_super_id")

        try:
            # Get the super_id
            table = s3db.del_master
            record = table[master_id]
            super_id = record["del_super_id"]

            # Create a component record
            component_id = component.insert(del_super_id=super_id)
            component_record = component[component_id]
            self.assertNotEqual(component_record, None)
            current.db.commit()

            # Delete the master record
            resource = s3db.resource("del_master", id=master_id)
            success = resource.delete()
            self.assertEqual(success, 1)
            self.assertEqual(resource.error, None)

            # Master record is deleted
            record = table[master_id]
            self.assertTrue(record.deleted)
            self.assertEqual(record.del_super_id, None)

            # Super-record is deleted
            stable = s3db.del_super
            srecord = stable[super_id]
            self.assertTrue(srecord.deleted)

            # Component record is deleted
            crecord = component[component_id]
            self.assertTrue(crecord.deleted)
            self.assertEqual(crecord.del_super_id, None)
            
            # Check callbacks
            self.assertEqual(self.master_deleted, master_id)
            self.assertEqual(self.super_deleted, super_id)
            self.assertEqual(self.component_deleted, component_id)

        finally:
            component.drop()
            del current.model.components["del_super"]["component"]

    # -------------------------------------------------------------------------
    def testArchiveSuperSetNull(self):
        """
            Test archiving of a super-entity instance record
            where the super-record is referenced by other records
            with SET NULL constraint
        """

        s3db = current.s3db

        master_id = self.master_id

        # Define component table
        s3db.define_table("del_component",
                          s3db.super_link("del_super_id",
                                          "del_super",
                                          ondelete="SET NULL"),
                          *s3_meta_fields())
        component = s3db["del_component"]
        s3db.add_components("del_super",
                            del_component="del_super_id")

        try:
            # Get the super_id
            table = s3db.del_master
            record = table[master_id]
            super_id = record["del_super_id"]

            # Create a component record
            component_id = component.insert(del_super_id=super_id)
            component_record = component[component_id]
            self.assertNotEqual(component_record, None)
            current.db.commit()

            # Delete the master record
            resource = s3db.resource("del_master", id=master_id)
            success = resource.delete()
            self.assertEqual(success, 1)
            self.assertEqual(resource.error, None)

            # Master record is deleted
            record = table[master_id]
            self.assertTrue(record.deleted)
            self.assertEqual(record.del_super_id, None)

            # Super-record is deleted
            stable = s3db.del_super
            srecord = stable[super_id]
            self.assertTrue(srecord.deleted)

            # Component record is not deleted, but unlinked
            crecord = component[component_id]
            self.assertFalse(crecord.deleted)
            self.assertEqual(crecord.del_super_id, None)
            
            # Check callbacks
            self.assertEqual(self.master_deleted, master_id)
            self.assertEqual(self.super_deleted, super_id)
            self.assertEqual(self.component_deleted, 0)

        finally:
            component.drop()
            del current.model.components["del_super"]["component"]

    # -------------------------------------------------------------------------
    def testArchiveSuperRestrict(self):
        """
            Test archiving of a super-entity instance record
            where the super-record is referenced by other records
            with RESTRICT constraint
        """

        s3db = current.s3db

        master_id = self.master_id

        # Define component table
        s3db.define_table("del_component",
                          s3db.super_link("del_super_id",
                                          "del_super",
                                          ondelete="RESTRICT"),
                          *s3_meta_fields())
        component = s3db["del_component"]
        s3db.add_components("del_super",
                            del_component="del_super_id")

        try:
            # Get the super_id
            table = s3db.del_master
            record = table[master_id]
            super_id = record["del_super_id"]

            # Create a component record
            component_id = component.insert(del_super_id=super_id)
            component_record = component[component_id]
            self.assertNotEqual(component_record, None)
            current.db.commit()

            # Delete the master record
            resource = s3db.resource("del_master", id=master_id)
            success = resource.delete()
            self.assertEqual(success, 0)
            self.assertEqual(resource.error, current.ERROR.INTEGRITY_ERROR)

            # Master record is not deleted
            record = table[master_id]
            self.assertFalse(record.deleted)
            self.assertEqual(record.del_super_id, super_id)

            # Super-record is not deleted
            stable = s3db.del_super
            srecord = stable[super_id]
            self.assertFalse(srecord.deleted)

            # Component record is not deleted and still unlinked
            crecord = component[component_id]
            self.assertFalse(crecord.deleted)
            self.assertEqual(crecord.del_super_id, super_id)
            
            # Check callbacks
            self.assertEqual(self.master_deleted, 0)
            self.assertEqual(self.super_deleted, 0)
            self.assertEqual(self.component_deleted, 0)

        finally:
            component.drop()
            del current.model.components["del_super"]["component"]
            
    ## -------------------------------------------------------------------------
    #def testDeleteSimple(self):
        #""" Test hard deletion of a record """

        #raise NotImplementedError

    ## -------------------------------------------------------------------------
    #def testDeleteCascade(self):
        #"""
            #Test hard deletion of a record which is referenced by
            #other records
        #"""
        
        #raise NotImplementedError

    ## -------------------------------------------------------------------------
    #def testDeleteSuper(self):
        #""" Test hard deletion of a super-entity instance record """

        #raise NotImplementedError

    ## -------------------------------------------------------------------------
    #def testDeleteSuperCascade(self):
        #"""
            #Test hard deletion of a super-entity instance record
            #where the super-record is referenced by other records
        #"""

        #raise NotImplementedError

# =============================================================================
def run_suite(*test_classes):
    """ Run the test suite """

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    if suite is not None:
        unittest.TextTestRunner(verbosity=2).run(suite)
    return

if __name__ == "__main__":

    run_suite(
        ComponentJoinConstructionTests,
        ComponentLeftJoinConstructionTests,

        FieldSelectorResolutionTests,

        ResourceFilterJoinTests,
        ResourceFilterQueryTests,
        ResourceContextFilterTests,

        URLQueryParserTests,

        URLQuerySerializerTests,
        URLFilterSerializerTests,

        ResourceFieldTests,
        ResourceLazyVirtualFieldsSupportTests,
        ResourceDataObjectAPITests,

        ResourceDataAccessTests,
        ResourceAxisFilterTests,
        ResourceDataTableFilterTests,
        ResourceGetTests,
        #ResourceInsertTest,
        #ResourceSelectTests,
        #ResourceUpdateTests,
        ResourceDeleteTests,

        #ResourceApproveTests,
        #ResourceRejectTests,

        #ResourceMergeTests,
        MergeOrganisationsTests,
        MergePersonsTests,
        MergeLocationsTests,
        MergeReferenceListsTest,

        ResourceExportTests,
        ResourceImportTests,
        ResourceFilteredComponentTests,
    )

# END ========================================================================
