#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from . import topic

LOG = log.get_logger()


class IOLinc(topic.SetTopic):
    """MQTT interface to an Insteon IOLinc device.

    This class connects to a device.IOLinc object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.IOLinc):  The Insteon object to link to.
        """
        super().__init__(mqtt, device)

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{"sensor": "{{sensor_on_str.lower()}}",' +
            ' "relay": "{{relay_on_str.lower()}}"}')

        # Output relay state change reporting template.
        self.msg_relay_state = MsgTemplate(
            topic='insteon/{{address}}/relay',
            payload='{{relay_on_str.lower()}}')

        # Output sensor state change reporting template.
        self.msg_sensor_state = MsgTemplate(
            topic='insteon/{{address}}/sensor',
            payload='{{sensor_on_str.lower()}}')

        device.signal_on_off.connect(self._insteon_on_off)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['io_linc'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("io_linc", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_relay_state.load_config(data, 'relay_state_topic',
                                         'relay_state_payload', qos)
        self.msg_sensor_state.load_config(data, 'sensor_state_topic',
                                          'sensor_state_payload', qos)
        self.load_set_data(data, qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # On/off command messages.
        self.set_subscribe(link, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        self.set_unsubscribe(link)

    #-----------------------------------------------------------------------
    def template_data(self, sensor_is_on=None, relay_is_on=None):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          is_on (bool):  The on/off state of the switch.  If None, on/off and
                mode attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = self.base_template_data()

        if sensor_is_on is not None:
            data["sensor_on"] = 1 if sensor_is_on else 0
            data["sensor_on_str"] = "on" if sensor_is_on else "off"
        if relay_is_on is not None:
            data["relay_on"] = 1 if relay_is_on else 0
            data["relay_on_str"] = "on" if relay_is_on else "off"

        return data

    #-----------------------------------------------------------------------
    def _insteon_on_off(self, device, sensor_is_on, relay_is_on):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes active or
        inactive.  It will publish an MQTT message with the new state.

        Args:
          device (device.IOLinc):   The Insteon device that changed.
          is_on (bool):   True for on, False for off.
        """
        LOG.info("MQTT received active change %s, sensor = %s relay = %s",
                 device.label, sensor_is_on, relay_is_on)

        data = self.template_data(sensor_is_on, relay_is_on)
        self.msg_state.publish(self.mqtt, data)
        self.msg_relay_state.publish(self.mqtt, data)
        self.msg_sensor_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
