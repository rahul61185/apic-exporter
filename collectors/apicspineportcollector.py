import re, logging
import BaseCollector
from prometheus_client.core import GaugeMetricFamily, Summary

LOG = logging.getLogger('apic_exporter.exporter')
REQUEST_TIME = Summary('apic_spine_ports_counter',
                       'Time spent processing request')

class ApicSpinePortsCollector(BaseCollector.BaseCollector):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.__metric_counter = 0
    def describe(self):
        yield GaugeMetricFamily('free_port_count',
                                'Total available free ports')

        yield GaugeMetricFamily('used_port_count',
                                'Total in-use ports')

        yield GaugeMetricFamily('down_port_count',
                                'In-use but down ports')

    @REQUEST_TIME.time()
    def collect(self):
        LOG.debug('Collecting APIC Spine ports metrics ...')

        g_free_port = GaugeMetricFamily(
            'free_port_count',
            'Total available free ports',
            labels=['apicHost', 'Spine_id', 'podId'])

        g_used_port = GaugeMetricFamily(
          'used_port_count',
            'Total in-use ports',
            labels=['apicHost', 'Spine_id', 'podId'])

        g_down_port = GaugeMetricFamily(
            'down_port_count',
            'In-use but down ports',
            labels=['apicHost', 'Spine_id', 'podId'])

        metric_counter = 0
        query_url = '/api/node/class/fabricNode.json?&query-target-filter=eq(fabricNode.role,"spine")&order-by=fabricNode.id|asc'
        for host in self.hosts:
            query = self.connection.getRequest(host, query_url)
            output  = json.loads(query.text)
            count = output['totalCount']
            spine_dn_list = []
            for x in range(0, int(count)):
                dn = str(output['imdata'][x]['fabricNode']['attributes']['dn'])
                spine_dn_list.append(str(dn))

            # fetch physcal port from each spine
            for dn in spine_dn_list:
                query_url = '/api/node/mo/'+ dn +'/sys.json?rsp-subtree=full&rsp-subtree-class=ethpmPhysIf'
                query = self.connection.getRequest(host, query_url)
                output  = json.loads(query.text)
                free_port_count = 0
                used_port_count = 0
                down_port_count = 0
                for x in output['imdata']:
                    pod_id = x['topSystem']['attributes']['podId']
                    spine_id = x['topSystem']['attributes']['id']
                    for port_dict in x['topSystem']['children']:
                        if (port_dict['l1PhysIf']['attributes']['adminSt'] == 'up') and (port_dict['l1PhysIf']['children'][0]['ethpmPhysIf']['attributes']['operSt'] == 'down'):
                            port_number = port_dict['l1PhysIf']['attributes']['id']
                            free_port_count += 1
                        elif (port_dict['l1PhysIf']['attributes']['adminSt'] == 'up') and (port_dict['l1PhysIf']['children'][0]['ethpmPhysIf']['attributes']['operSt'] == 'up'):
                            port_number = port_dict['l1PhysIf']['attributes']['id']
                            used_port_count +=1
                        elif port_dict['l1PhysIf']['attributes']['adminSt'] == 'down':
                            port_number = port_dict['l1PhysIf']['attributes']['id']
                            down_port_count +=1
                    # Free Ports
                    g_free_port.add_metric(
                        labels=[host, spine_id, 'podId'],
                        value=free_port_count

                    # Used Ports
                    g_used_port.add_metric(
                        labels=[host, spine_id, 'podId'],
                        value=used_port_count
                    
                    # Down ports
                    g_down_port.add_metric(
                        labels=[host, spine_id, 'podId'],
                        value=down_port_count
            break  # Each host produces the same metrics.

        yield g_free_port_count
        yield g_used_port_count
        yield g_down_port_count

        LOG.info('Collected %s APIC Spine ports metrics')
