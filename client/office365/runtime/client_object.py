import importlib

from client.office365.runtime.odata.odata_path_parser import ODataPathParser
from client.office365.runtime.odata.sharepoint_metadata_type import SharePointMetadataType


class ClientObject(object):
    """Base client object"""

    def __init__(self, context, resource_path=None, properties=None):
        if properties is None:
            properties = {}
        self._entity_type_name = None
        self._query_options = {}
        self._parent_collection = None
        self._context = context
        self._properties = properties
        self._changed_properties = properties
        self._resource_path = resource_path
        self._url = None

    @property
    def include_metadata(self):
        if self.context.json_format.metadata == SharePointMetadataType.NoMetadata \
                or self.context.json_format.metadata == SharePointMetadataType.MinimalMetadata:
            return False
        return True

    @property
    def entity_type_name(self):
        if self._entity_type_name is None:
            self._entity_type_name = "SP." + type(self).__name__
        return self._entity_type_name

    @entity_type_name.setter
    def entity_type_name(self, value):
        self._entity_type_name = value

    def ensure_metadata_type(self, entity):
        """Ensures metadata type is contained in payload"""
        if '__metadata' not in entity:
            entity["__metadata"] = {'type': self.entity_type_name}

    def create_typed_object(self, properties):
        entity_name = self.__class__.__name__.replace("Collection", "")
        module_name = self.context.__module__.replace("client_context", "") + entity_name.lower()
        clientObjectClass = getattr(importlib.import_module(module_name), entity_name)
        client_object = clientObjectClass(self.context)
        client_object.from_json(properties)
        return client_object

    def remove_from_parent_collection(self):
        if self._parent_collection is None:
            return
        self._parent_collection.remove(self)

    def is_property_available(self, name):
        """Returns a Boolean value that indicates whether the specified property has been retrieved or set."""
        if name in self.properties and '__deferred' not in self.properties[name]:
            return True
        return False

    def query_options_to_url(self):
        """Convert query options to url"""
        return '&'.join(['$%s=%s' % (key, value) for (key, value) in self.query_options.items()])

    def set_property(self, name, value, persist_changes=True):
        """Set resource property"""
        if persist_changes:  # persist properties
            self._changed_properties[name] = value
        self._properties[name] = value

    @property
    def context(self):
        return self._context

    @property
    def service_root_url(self):
        return self.context.service_root_url

    @property
    def resource_path(self):
        return self._resource_path

    @property
    def query_options(self):
        return self._query_options

    @property
    def url(self):
        if self._url:
            return self._url
        else:
            self._url = self.service_root_url + self.resource_path.build_path_url()
        if self.query_options:
            self._url = self._url + "?" + self.query_options_to_url()
        return self._url

    @property
    def type_name(self):
        return self.__module__ + "." + self.__class__.__name__

    @property
    def properties(self):
        return self._properties

    def to_json(self):
        """Generates resource payload for REST endpoint"""
        payload = dict(self._changed_properties)
        if self.include_metadata:
            self.ensure_metadata_type(payload)
        else:
            payload = dict((k, v) for k, v in payload.iteritems() if k != "__metadata")
        return payload

    def from_json(self, payload):
        self._properties = dict((k, v) for k, v in payload.iteritems()
                                if k != '__metadata')
        if '__metadata' in payload:
            self._url = payload['__metadata']['uri']
            self._resource_path = ODataPathParser.parse_path_string(self._url)
            self._entity_type_name = payload['__metadata']['type']
