# -*- coding: utf-8 -*-
import unittest
import mock
import tempfile

from tutumcli.utils import *
from tutumcli.exceptions import *
from tutum.api.exceptions import *


class TabulateResultTestCase(unittest.TestCase):
    @mock.patch('tutumcli.utils.tabulate')
    def test_tabulate_result(self, mock_tabulate):
        data_list = None
        headers = None
        tabulate_result(data_list, headers)
        mock_tabulate.assert_called_with(data_list, headers, stralign="left", tablefmt="plain")


class DateTimeConversionTestCase(unittest.TestCase):
    def test_from_utc_string_to_utc_datetime(self):
        # test None
        self.assertIsNone(from_utc_string_to_utc_datetime(None))

        # test mal-formatted string
        self.assertRaises(Exception, from_utc_string_to_utc_datetime, 'abc')

        # test normal case
        utc_datetime = from_utc_string_to_utc_datetime('Sun, 6 Apr 2014 18:11:17 +0000')
        self.assertEqual(str(utc_datetime), '2014-04-06 18:11:17')

    def test_get_humanize_local_datetime_from_utc_datetime_string(self):
        # test None
        self.assertEqual(get_humanize_local_datetime_from_utc_datetime_string(None), '')

        # test mal-formatted string
        self.assertRaises(Exception, get_humanize_local_datetime_from_utc_datetime_string, 'abc')

        # test normal case
        utc_datetime = get_humanize_local_datetime_from_utc_datetime_string('Sun, 6 Apr 2014 18:11:17 +0000')
        self.assertRegexpMatches(utc_datetime, r".* ago")

        # test future
        utc_datetime = get_humanize_local_datetime_from_utc_datetime_string('Sun, 6 Apr 3014 18:11:17 +0000')
        self.assertNotRegexpMatches(utc_datetime, r".* ago")


class IsUuidTestCase(unittest.TestCase):
    def test_is_uuid4(self):
        self.assertTrue(is_uuid4('7a4cfe51-038b-42d6-825e-3b533888d8cd'))
        self.assertTrue(is_uuid4('7A4CFE51-03BB-42D6-825E-3B533888D8CD'))

        self.assertFalse(is_uuid4('not_uuid'))
        self.assertFalse(is_uuid4(''))
        self.assertRaises(Exception, is_uuid4, None)
        self.assertRaises(Exception, is_uuid4, 12345)


class AddUnicodeSymbolToStateTestCase(unittest.TestCase):
    def test_add_unicode_symbol_to_state(self):
        for state in ['Running', 'Partly running']:
            self.assertEqual(' '.join([u'▶', state]), add_unicode_symbol_to_state(state))
        for state in ['Init', 'Stopped']:
            self.assertEqual(' '.join([u'◼', state]), add_unicode_symbol_to_state(state))
        for state in ['Starting', 'Stopping', 'Scaling', 'Terminating']:
            self.assertEqual(' '.join([u'⚙', state]), add_unicode_symbol_to_state(state))
        for state in ['Start failed', 'Stopped with errors']:
            self.assertEqual(' '.join([u'!', state]), add_unicode_symbol_to_state(state))
        for state in ['Terminated']:
            self.assertEqual(' '.join([u'✘', state]), add_unicode_symbol_to_state(state))


class GetDockerClientTestCase(unittest.TestCase):
    @mock.patch('tutumcli.utils.docker')
    def test_get_docker_client(self, mock_docker):
        get_docker_client()
        mock_docker.Client.assert_called_with(base_url=getenv("DOCKER_HOST"))

    @mock.patch('tutumcli.utils.getenv')
    def test_get_docker_client_exception(self, mock_getenv):
        mock_getenv.return_value = '/run/mock.docker.sock'
        self.assertRaises(DockerNotFound, get_docker_client)


class BuildDockerfileTestCase(unittest.TestCase):
    def test_build_dockerfile_with_ports(self):
        output = '''FROM tutum/buildstep

EXPOSE 8080 8888

CMD [/bin/bash,/run.sh]'''
        fd, filepath = tempfile.mkstemp()
        ports = "8080 8888"
        commands = ["/bin/bash", "/run.sh"]
        build_dockerfile(filepath, ports, commands)
        file = open(filepath, 'r')
        try:
            data = file.read()
            self.assertEqual(output, data)
        finally:
            os.close(fd)
            file.close()
            os.remove(filepath)

    def test_build_dockerfile_without_ports(self):
        output = '''FROM tutum/buildstep

CMD [/bin/bash,/run.sh]'''
        fd, filepath = tempfile.mkstemp()
        ports = None
        commands = ["/bin/bash", "/run.sh"]
        build_dockerfile(filepath, ports, commands)
        file = open(filepath, 'r')
        try:
            data = file.read()
            self.assertEqual(output, data)
        finally:
            os.close(fd)
            file.close()
            os.remove(filepath)

    def test_build_dockerfile_string_commands(self):
        output = '''FROM tutum/buildstep

CMD /bin/bash /run.sh'''
        fd, filepath = tempfile.mkstemp()
        ports = None
        commands = "/bin/bash /run.sh"
        build_dockerfile(filepath, ports, commands)
        file = open(filepath, 'r')
        try:
            data = file.read()
            self.assertEqual(output, data)
        finally:
            os.close(fd)
            file.close()
            os.remove(filepath)


class FetchRemoteObjectTestCase(unittest.TestCase):
    @mock.patch('tutumcli.utils.tutum.Container.list')
    @mock.patch('tutumcli.utils.tutum.Container.fetch')
    def test_fetch_remote_container(self, mock_fetch, mock_list):
        # test container exist queried with uuid4
        mock_fetch.return_value = 'returned'
        self.assertEqual(fetch_remote_container('7A4CFE51-03BB-42D6-825E-3B533888D8CD', True), 'returned')
        self.assertEqual(fetch_remote_container('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), 'returned')

        # test container doesn't exist queried with uuid4
        mock_fetch.side_effect = ObjectNotFound
        self.assertRaises(ObjectNotFound, fetch_remote_container, '7A4CFE51-03BB-42D6-825E-3B533888D8CD', True)
        self.assertIsInstance(fetch_remote_container('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), ObjectNotFound)

        # test unique container found queried with short uuid
        mock_list.side_effect = [['container'], []]
        self.assertEquals(fetch_remote_container('shortuuid', True), 'container')
        mock_list.side_effect = [['container'], []]
        self.assertEquals(fetch_remote_container('shortuuid', False), 'container')

        # test unique container found queried with name
        mock_list.side_effect = [[], ['container']]
        self.assertEquals(fetch_remote_container('name', True), 'container')
        mock_list.side_effect = [[], ['container']]
        self.assertEquals(fetch_remote_container('name', False), 'container')

        # test no container found
        mock_list.side_effect = [[], []]
        self.assertRaises(ObjectNotFound, fetch_remote_container, 'uuid_or_name', True)
        mock_list.side_effect = [[], []]
        self.assertIsInstance(fetch_remote_container('uuid_or_name', False), ObjectNotFound)

        # test multi-container found
        mock_list.side_effect = [['container1', 'container2'], []]
        self.assertRaises(NonUniqueIdentifier, fetch_remote_container, 'uuid_or_name', True)
        mock_list.side_effect = [['container1', 'container2'], []]
        self.assertIsInstance(fetch_remote_container('uuid_or_name', False), NonUniqueIdentifier)
        mock_list.side_effect = [[], ['container1', 'container2']]
        self.assertRaises(NonUniqueIdentifier, fetch_remote_container, 'uuid_or_name', True)
        mock_list.side_effect = [[], ['container1', 'container2']]
        self.assertIsInstance(fetch_remote_container('uuid_or_name', False), NonUniqueIdentifier)

        # test api error
        mock_list.side_effect = [TutumApiError, TutumApiError]
        self.assertRaises(TutumApiError, fetch_remote_container, 'uuid_or_name', True)
        self.assertRaises(TutumApiError, fetch_remote_container, 'uuid_or_name', False)

    @mock.patch('tutumcli.utils.tutum.Service.list')
    @mock.patch('tutumcli.utils.tutum.Service.fetch')
    def test_fetch_remote_service(self, mock_fetch, mock_list):
        # test cluster exist queried with uuid4
        mock_fetch.return_value = 'returned'
        self.assertEqual(fetch_remote_service('7A4CFE51-03BB-42D6-825E-3B533888D8CD', True), 'returned')
        self.assertEqual(fetch_remote_service('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), 'returned')

        # test cluster doesn't exist queried with uuid4
        mock_fetch.side_effect = ObjectNotFound
        self.assertRaises(ObjectNotFound, fetch_remote_service, '7A4CFE51-03BB-42D6-825E-3B533888D8CD', True)
        self.assertIsInstance(fetch_remote_service('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), ObjectNotFound)

        # test unique cluster found queried with short uuid
        mock_list.side_effect = [['cluster'], []]
        self.assertEquals(fetch_remote_service('shortuuid', True), 'cluster')
        mock_list.side_effect = [['cluster'], []]
        self.assertEquals(fetch_remote_service('shortuuid', False), 'cluster')

        # test unique cluster found queried with name
        mock_list.side_effect = [[], ['cluster']]
        self.assertEquals(fetch_remote_service('name', True), 'cluster')
        mock_list.side_effect = [[], ['cluster']]
        self.assertEquals(fetch_remote_service('name', False), 'cluster')

        # test no cluster found
        mock_list.side_effect = [[], []]
        self.assertRaises(ObjectNotFound, fetch_remote_service, 'uuid_or_name', True)
        mock_list.side_effect = [[], []]
        self.assertIsInstance(fetch_remote_service('uuid_or_name', False), ObjectNotFound)

        # test multi-cluster found
        mock_list.side_effect = [['cluster1', 'cluster2'], []]
        self.assertRaises(NonUniqueIdentifier, fetch_remote_service, 'uuid_or_name', True)
        mock_list.side_effect = [['cluster1', 'cluster2'], []]
        self.assertIsInstance(fetch_remote_service('uuid_or_name', False), NonUniqueIdentifier)
        mock_list.side_effect = [[], ['cluster1', 'cluster2']]
        self.assertRaises(NonUniqueIdentifier, fetch_remote_service, 'uuid_or_name', True)
        mock_list.side_effect = [[], ['cluster1', 'cluster2']]
        self.assertIsInstance(fetch_remote_service('uuid_or_name', False), NonUniqueIdentifier)

        # test api error
        mock_list.side_effect = [TutumApiError, TutumApiError]
        self.assertRaises(TutumApiError, fetch_remote_service, 'uuid_or_name', True)
        self.assertRaises(TutumApiError, fetch_remote_service, 'uuid_or_name', False)

    @mock.patch('tutumcli.utils.tutum.Node.list')
    @mock.patch('tutumcli.utils.tutum.Node.fetch')
    def test_fetch_remote_node(self, mock_fetch, mock_list):
        # test node exist queried with uuid4
        mock_fetch.return_value = 'returned'
        self.assertEqual(fetch_remote_node('7A4CFE51-03BB-42D6-825E-3B533888D8CD', True), 'returned')
        self.assertEqual(fetch_remote_node('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), 'returned')

        # test node doesn't exist queried with uuid4
        mock_fetch.side_effect = ObjectNotFound
        self.assertRaises(ObjectNotFound, fetch_remote_node, '7A4CFE51-03BB-42D6-825E-3B533888D8CD', True)
        self.assertIsInstance(fetch_remote_node('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), ObjectNotFound)


        # test unique node found queried with short uuid
        mock_list.side_effect = [['node']]
        self.assertEquals(fetch_remote_node('uuid', True), 'node')
        mock_list.side_effect = [['node']]
        self.assertEquals(fetch_remote_node('uuid', False), 'node')

        # test no node found
        mock_list.side_effect = [[]]
        self.assertRaises(ObjectNotFound, fetch_remote_node, 'uuid', True)
        mock_list.side_effect = [[]]
        self.assertIsInstance(fetch_remote_node('uuid', False), ObjectNotFound)

        # test multi-node found
        mock_list.side_effect = [['node1', 'node2']]
        self.assertRaises(NonUniqueIdentifier, fetch_remote_node, 'uuid', True)
        mock_list.side_effect = [['node1', 'node2']]
        self.assertIsInstance(fetch_remote_node('uuid', False), NonUniqueIdentifier)

        # test api error
        mock_list.side_effect = [TutumApiError, TutumApiError]
        self.assertRaises(TutumApiError, fetch_remote_node, 'uuid', True)
        self.assertRaises(TutumApiError, fetch_remote_node, 'uuid', False)

    @mock.patch('tutumcli.utils.tutum.NodeCluster.list')
    @mock.patch('tutumcli.utils.tutum.NodeCluster.fetch')
    def test_fetch_remote_nodecluster(self, mock_fetch, mock_list):
        # test nodecluster exist queried with uuid4
        mock_fetch.return_value = 'returned'
        self.assertEqual(fetch_remote_nodecluster('7A4CFE51-03BB-42D6-825E-3B533888D8CD', True), 'returned')
        self.assertEqual(fetch_remote_nodecluster('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), 'returned')

        # test nodecluster doesn't exist queried with uuid4
        mock_fetch.side_effect = ObjectNotFound
        self.assertRaises(ObjectNotFound, fetch_remote_nodecluster, '7A4CFE51-03BB-42D6-825E-3B533888D8CD', True)
        self.assertIsInstance(fetch_remote_nodecluster('7A4CFE51-03BB-42D6-825E-3B533888D8CD', False), ObjectNotFound)

        # test unique nodecluster found queried with short uuid
        mock_list.side_effect = [['nodecluster'], []]
        self.assertEquals(fetch_remote_nodecluster('shortuuid', True), 'nodecluster')
        mock_list.side_effect = [['nodecluster'], []]
        self.assertEquals(fetch_remote_nodecluster('shortuuid', False), 'nodecluster')

        # test unique nodecluster found queried with name
        mock_list.side_effect = [[], ['nodecluster']]
        self.assertEquals(fetch_remote_nodecluster('name', True), 'nodecluster')
        mock_list.side_effect = [[], ['nodecluster']]
        self.assertEquals(fetch_remote_nodecluster('name', False), 'nodecluster')

        # test no nodecluster found
        mock_list.side_effect = [[], []]
        self.assertRaises(ObjectNotFound, fetch_remote_nodecluster, 'uuid_or_name', True)
        mock_list.side_effect = [[], []]
        self.assertIsInstance(fetch_remote_nodecluster('uuid_or_name', False), ObjectNotFound)

        # test multi-nodecluster found
        mock_list.side_effect = [['nodecluster1', 'nodecluster2'], []]
        self.assertRaises(NonUniqueIdentifier, fetch_remote_nodecluster, 'uuid_or_name', True)
        mock_list.side_effect = [['nodecluster1', 'nodecluster2'], []]
        self.assertIsInstance(fetch_remote_nodecluster('uuid_or_name', False), NonUniqueIdentifier)
        mock_list.side_effect = [[], ['nodecluster1', 'nodecluster2']]
        self.assertRaises(NonUniqueIdentifier, fetch_remote_nodecluster, 'uuid_or_name', True)
        mock_list.side_effect = [[], ['nodecluster1', 'nodecluster2']]
        self.assertIsInstance(fetch_remote_nodecluster('uuid_or_name', False), NonUniqueIdentifier)

        # test api error
        mock_list.side_effect = [TutumApiError, TutumApiError]
        self.assertRaises(TutumApiError, fetch_remote_nodecluster, 'uuid_or_name', True)
        self.assertRaises(TutumApiError, fetch_remote_nodecluster, 'uuid_or_name', False)


class ParseLinksTestCase(unittest.TestCase):
    def test_parse_links(self):
        output = [{'to_container': 'mysql', 'name': 'db1'}, {'to_container': 'mariadb', 'name': 'db2'}]
        self.assertEqual(output, parse_links(['mysql:db1', 'mariadb:db2'], 'to_container'))

    def test_parse_links_bad_format(self):
        self.assertRaises(BadParameter, parse_links, ['mysql', 'mariadb'], 'to_container')
        self.assertRaises(BadParameter, parse_links, ['mysql:mysql:mysql', 'mariadb:maria:maria'], 'to_container')
        self.assertRaises(BadParameter, parse_links, [''], 'to_container')


class ParsePortsTestCase(unittest.TestCase):
    def test_parse_ports(self):
        output = [{'protocol': 'tcp', 'inner_port': '80'}]
        self.assertEqual(output, parse_ports(['80']))

        output = [{'protocol': 'tcp', 'inner_port': '80'},
                  {'protocol': 'udp', 'inner_port': '53'},
                  {'protocol': 'tcp', 'inner_port': '3306', 'outer_port': '3307'},
                  {'protocol': 'udp', 'inner_port': '8080', 'outer_port': '8083'}]
        self.assertEqual(output, parse_ports(['80', '53/udp', '3307:3306', '8083:8080/udp']))

    def test_parse_ports_bad_format(self):
        self.assertRaises(BadParameter, parse_ports, ['abc'])
        self.assertRaises(BadParameter, parse_ports, ['abc:80'])
        self.assertRaises(BadParameter, parse_ports, ['80:abc'])
        self.assertRaises(BadParameter, parse_ports, ['80:80:abc'])
        self.assertRaises(BadParameter, parse_ports, ['80:80/abc'])
        self.assertRaises(BadParameter, parse_ports, ['80/80:tcp'])
        self.assertRaises(BadParameter, parse_ports, [''])


class ParseEnvironmentVariablesTestCase(unittest.TestCase):
    def test_parse_envvars(self):
        output = [{'key': 'MYSQL_USER', 'value': 'admin'}, {'key': 'MYSQL_PASS', 'value': 'mypass'}]
        self.assertEqual(output, parse_envvars(['MYSQL_USER=admin', 'MYSQL_PASS=mypass']))

    def test_parse_envvars(self):
        self.assertRaises(BadParameter, parse_envvars, ['MYSQL_ADMIN'])
        self.assertRaises(BadParameter, parse_envvars, ['1MYSQL_ADMIN=mypass'])
        self.assertRaises(BadParameter, parse_envvars, ['MYSQL_ADMIN==mypass'])
        self.assertRaises(BadParameter, parse_envvars, ['MYSQL_ADMIN=m!ypass'])
        self.assertRaises(BadParameter, parse_envvars, ['MYSQL_ADMIN=my?pass'])
        self.assertRaises(BadParameter, parse_envvars, ['MYSQL_ADMIN=mypass=113'])
        self.assertRaises(BadParameter, parse_envvars, ['MYSQL_ADMIN='])
