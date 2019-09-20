import pysnow as sn
import re
import sys
import json, ast


from st2reactor.sensor.base import PollingSensor
from st2reactor.sensor.base import Sensor

reload(sys)
sys.setdefaultencoding('utf8')


class TaskInfoSensor(PollingSensor):
    def __init__(self, sensor_service, config, poll_interval=5):
        super(TaskInfoSensor, self).__init__(sensor_service=sensor_service, config=config, poll_interval=poll_interval) #, poll_interval=poll_interval
        
        #self._poll_interval = poll_interval

        self._trigger_ref = 'servicenow.taskinfo'
        self._logger = self.sensor_service.get_logger(name=self.__class__.__name__)
        self._stop = False


    def setup(self):
        instance_name = self.config['instance_name']
        username = self.config['username']
        password = self.config['password']

        # Getting values from pack sensors section
        self.state = self._get_config_entry('state', prefix='sensors.taskinfo')
        self.assignment_group = self._get_config_entry('assignment_group', prefix='sensors.taskinfo')
        self.short_description = self._get_config_entry('short_description', prefix='sensors.taskinfo')
        self.table = self._get_config_entry('table', prefix='sensors.taskinfo')

        self.client = sn.Client(instance=instance_name, user=username, password=password)

        self._last_id = None

        if 'custom_params' in self.config and isinstance(self.config['custom_params'], dict):
            self.client.parameters.add_custom(self.config['custom_params'])


    def poll(self):
        last_id = self._get_last_id()

        #if last_id:
        #    tso.set_since_id(int(last_id))
        try:
            records = self._get_task_collector()
            self._logger.debug('Found a TaskInfo: %s' % records['short_description'])
        except Exception as e:
            self._logger.debug('Polling TaskInfo failed: %s' % (str(e)))
        #if self._get_task_collector():
        #    record = self._get_task_collector()
        #    self._logger.debug('Found a TaskInfo: %s' % record['short_description'])

        # dispatches taskinfo trigger
        for record in records:
            #if record['short_description'] in ['get_storage_wwn', 'get_vm_storage_wwn', 'vm_migrate_cluster_ds']:
            if record['description']:
                self._dispatch_taskinfo(record)


    def _get_task_collector(self):
        api_path = '/table/{}'.format(self.table)
        query = {
            'assignment_group': self.assignment_group, 
            'state': self.state, 
            'active': True
        }

        r = self.client.resource(api_path=api_path)
        response = r.get(query=query)

        try:
            return response.all()
        except Exception as e:
            self._logger.error(e)


    def _get_last_id(self):
        if not self._last_id and hasattr(self._sensor_service, 'get_value'):
            self._last_id = self._sensor_service.get_value(name='last_id')

        return self._last_id


    def _set_last_id(self, last_id):
        self._last_id = last_id

        if hasattr(self._sensor_service, 'set_value'):
            self._sensor_service.set_value(name='last_id', value=last_id)


    def _remove_tags(self, description):
        removed_tags = re.compile(r'<[^>]+>')
        return removed_tags.sub('', description)


    def _dispatch_taskinfo(self, taskinfo):
        description = self._remove_tags(taskinfo['description'])
        if taskinfo['short_description'] in ['vm_migrate_cluster_ds', 'vm_migrate_cluster_ds_iso']:
            trigger = 'servicenow.vm_migration'
            d = json.loads(description)
            payload = {
                'sys_id': str(taskinfo['sys_id']),
                'table': str(self.table),
                'short_description': str(taskinfo['short_description']),
                'state': int(taskinfo['state']),
                'vm_name': str(d['name']),
                'cluster': str(d['cluster'])
            }
            self.sensor_service.dispatch(trigger=trigger, payload=payload)
        elif taskinfo['short_description'] in ['get_storage_wwn', 'get_vm_storage_wwn']:
            trigger = self._trigger_ref
            r_list = description.split(",")
            resources = ast.literal_eval(json.dumps((r_list)))

            payload = {
                'sys_id': str(taskinfo['sys_id']),
                'short_description': str(taskinfo['short_description']),
                'state': int(taskinfo['state']),
                'description': str(resources),
                'table': str(self.table)
            }
            self.sensor_service.dispatch(trigger=trigger, payload=payload)


    def _get_config_entry(self, key, prefix=None):
        # First of all, get configuration value from Datastore
        value = self.sensor_service.get_value('servicenow.%s' % (key), local=False)
        if value:
            return value

        # Then, get it from the configuration file
        config = self.config
        if prefix:
            for _prefix in prefix.split('.'):
                config = config.get(_prefix, {})

        return config.get(key, None)


    def cleanup(self):
        self._stop = True


    # Methods required for programmable sensors.
    def add_trigger(self, trigger):
        pass


    def update_trigger(self, trigger):
        pass


    def remove_trigger(self, trigger):
        pass
