"""Generated message classes for container version v1beta1.

The Google Container Engine API is used for building and managing container
based applications, powered by the open source Kubernetes technology.
"""
# NOTE: This file is autogenerated and should not be edited by hand.

from protorpc import messages as _messages


package = 'container'


class Cluster(_messages.Message):
  """A Cluster object.

  Enums:
    StatusValueValuesEnum: [Output only] The current status of this cluster.

  Fields:
    clusterApiVersion: The API version of the Kubernetes master and kubelets
      running in this cluster. Leave blank to pick up the latest stable
      release, or specify a version of the form "x.y.z". The Google Container
      Engine release notes lists the currently supported versions. If an
      incorrect version is specified, the server returns an error listing the
      currently supported versions.
    containerIpv4Cidr: The IP address range of the container pods in this
      cluster, in  CIDR notation (e.g. 10.96.0.0/14). Leave blank to have one
      automatically chosen or specify a /14 block in 10.0.0.0/8 or
      172.16.0.0/12.
    creationTimestamp: [Output only] The time the cluster was created, in
      RFC3339 text format.
    description: An optional description of this cluster.
    enableCloudLogging: Whether logs from the cluster should be made available
      via the Google Cloud Logging service. This includes both logs from your
      applications running in the cluster as well as logs from the Kubernetes
      components themselves.
    enableCloudMonitoring: Whether metrics from the cluster should be made
      available via the Google Cloud Monitoring service.
    endpoint: [Output only] The IP address of this cluster's Kubernetes
      master. The endpoint can be accessed from the internet at
      https://username:password@endpoint/.  See the masterAuth property of
      this resource for username and password information.
    instanceGroupUrls: [Output only] The resource URLs of [instance
      groups](/compute/docs/instance-groups/) associated with this cluster.
    masterAuth: The authentication information for accessing the master.
    name: The name of this cluster. The name must be unique within this
      project and zone, and can be up to 40 characters with the following
      restrictions:   - Lowercase letters, numbers, and hyphens only. - Must
      start with a letter. - Must end with a number or a letter.
    network: The name of the Google Compute Engine network to which the
      cluster is connected.
    nodeConfig: The machine type and image to use for all nodes in this
      cluster. See the descriptions of the child properties of nodeConfig.
    nodeRoutingPrefixSize: [Output only] The size of the address space on each
      node for hosting containers.
    numNodes: The number of nodes to create in this cluster. You must ensure
      that your Compute Engine resource quota is sufficient for this number of
      instances plus one (to include the master). You must also have available
      firewall and routes quota.
    selfLink: [Output only] Server-defined URL for the resource.
    servicesIpv4Cidr: [Output only] The IP address range of the Kubernetes
      services in this cluster, in  CIDR notation (e.g. 1.2.3.4/29). Service
      addresses are typically put in the last /16 from the container CIDR.
    status: [Output only] The current status of this cluster.
    statusMessage: [Output only] Additional information about the current
      status of this cluster, if available.
    zone: [Output only] The name of the Google Compute Engine zone in which
      the cluster resides.
  """

  class StatusValueValuesEnum(_messages.Enum):
    """[Output only] The current status of this cluster.

    Values:
      error: <no description>
      provisioning: <no description>
      running: <no description>
      stopping: <no description>
    """
    error = 0
    provisioning = 1
    running = 2
    stopping = 3

  clusterApiVersion = _messages.StringField(1)
  containerIpv4Cidr = _messages.StringField(2)
  creationTimestamp = _messages.StringField(3)
  description = _messages.StringField(4)
  enableCloudLogging = _messages.BooleanField(5)
  enableCloudMonitoring = _messages.BooleanField(6)
  endpoint = _messages.StringField(7)
  instanceGroupUrls = _messages.StringField(8, repeated=True)
  masterAuth = _messages.MessageField('MasterAuth', 9)
  name = _messages.StringField(10)
  network = _messages.StringField(11)
  nodeConfig = _messages.MessageField('NodeConfig', 12)
  nodeRoutingPrefixSize = _messages.IntegerField(13, variant=_messages.Variant.INT32)
  numNodes = _messages.IntegerField(14, variant=_messages.Variant.INT32)
  selfLink = _messages.StringField(15)
  servicesIpv4Cidr = _messages.StringField(16)
  status = _messages.EnumField('StatusValueValuesEnum', 17)
  statusMessage = _messages.StringField(18)
  zone = _messages.StringField(19)


class ContainerProjectsClustersListRequest(_messages.Message):
  """A ContainerProjectsClustersListRequest object.

  Fields:
    projectId: The Google Developers Console project ID or  project number.
  """

  projectId = _messages.StringField(1, required=True)


class ContainerProjectsOperationsListRequest(_messages.Message):
  """A ContainerProjectsOperationsListRequest object.

  Fields:
    projectId: The Google Developers Console project ID or  project number.
  """

  projectId = _messages.StringField(1, required=True)


class ContainerProjectsZonesClustersCreateRequest(_messages.Message):
  """A ContainerProjectsZonesClustersCreateRequest object.

  Fields:
    createClusterRequest: A CreateClusterRequest resource to be passed as the
      request body.
    projectId: The Google Developers Console project ID or  project number.
    zoneId: The name of the Google Compute Engine zone in which the cluster
      resides.
  """

  createClusterRequest = _messages.MessageField('CreateClusterRequest', 1)
  projectId = _messages.StringField(2, required=True)
  zoneId = _messages.StringField(3, required=True)


class ContainerProjectsZonesClustersDeleteRequest(_messages.Message):
  """A ContainerProjectsZonesClustersDeleteRequest object.

  Fields:
    clusterId: The name of the cluster to delete.
    projectId: The Google Developers Console project ID or  project number.
    zoneId: The name of the Google Compute Engine zone in which the cluster
      resides.
  """

  clusterId = _messages.StringField(1, required=True)
  projectId = _messages.StringField(2, required=True)
  zoneId = _messages.StringField(3, required=True)


class ContainerProjectsZonesClustersGetRequest(_messages.Message):
  """A ContainerProjectsZonesClustersGetRequest object.

  Fields:
    clusterId: The name of the cluster to retrieve.
    projectId: The Google Developers Console project ID or  project number.
    zoneId: The name of the Google Compute Engine zone in which the cluster
      resides.
  """

  clusterId = _messages.StringField(1, required=True)
  projectId = _messages.StringField(2, required=True)
  zoneId = _messages.StringField(3, required=True)


class ContainerProjectsZonesClustersListRequest(_messages.Message):
  """A ContainerProjectsZonesClustersListRequest object.

  Fields:
    projectId: The Google Developers Console project ID or  project number.
    zoneId: The name of the Google Compute Engine zone in which the cluster
      resides.
  """

  projectId = _messages.StringField(1, required=True)
  zoneId = _messages.StringField(2, required=True)


class ContainerProjectsZonesOperationsGetRequest(_messages.Message):
  """A ContainerProjectsZonesOperationsGetRequest object.

  Fields:
    operationId: The server-assigned name of the operation.
    projectId: The Google Developers Console project ID or  project number.
    zoneId: The name of the Google Compute Engine zone in which the operation
      resides. This is always the same zone as the cluster with which the
      operation is associated.
  """

  operationId = _messages.StringField(1, required=True)
  projectId = _messages.StringField(2, required=True)
  zoneId = _messages.StringField(3, required=True)


class ContainerProjectsZonesOperationsListRequest(_messages.Message):
  """A ContainerProjectsZonesOperationsListRequest object.

  Fields:
    projectId: The Google Developers Console project ID or  project number.
    zoneId: The name of the Google Compute Engine zone to return operations
      for.
  """

  projectId = _messages.StringField(1, required=True)
  zoneId = _messages.StringField(2, required=True)


class CreateClusterRequest(_messages.Message):
  """A CreateClusterRequest object.

  Fields:
    cluster: A cluster resource.
  """

  cluster = _messages.MessageField('Cluster', 1)


class ListAggregatedClustersResponse(_messages.Message):
  """A ListAggregatedClustersResponse object.

  Fields:
    clusters: A list of clusters in the project, across all zones.
  """

  clusters = _messages.MessageField('Cluster', 1, repeated=True)


class ListAggregatedOperationsResponse(_messages.Message):
  """A ListAggregatedOperationsResponse object.

  Fields:
    operations: A list of operations in the project, across all zones.
  """

  operations = _messages.MessageField('Operation', 1, repeated=True)


class ListClustersResponse(_messages.Message):
  """A ListClustersResponse object.

  Fields:
    clusters: A list of clusters in the project in the specified zone.
  """

  clusters = _messages.MessageField('Cluster', 1, repeated=True)


class ListOperationsResponse(_messages.Message):
  """A ListOperationsResponse object.

  Fields:
    operations: A list of operations in the project in the specified zone.
  """

  operations = _messages.MessageField('Operation', 1, repeated=True)


class MasterAuth(_messages.Message):
  """The authentication information for accessing the master. Authentication
  is either done using HTTP basic authentication or using a bearer token.

  Fields:
    bearerToken: The token used to authenticate API requests to the master.
      The token is to be included in an HTTP Authorization Header in all
      requests to the master endpoint. The format of the header is:
      "Authorization: Bearer ".
    clientCertificate: [Output only] Base64 encoded public certificate used by
      clients to authenticate to the cluster endpoint.
    clientKey: [Output only] Base64 encoded private key used by clients to
      authenticate to the cluster endpoint.
    clusterCaCertificate: [Output only] Base64 encoded public certificate that
      is the root of trust for the cluster.
    password: The password to use for HTTP basic authentication when accessing
      the Kubernetes master endpoint. Because the master endpoint is open to
      the internet, you should create a strong password.
    user: The username to use for HTTP basic authentication when accessing the
      Kubernetes master endpoint.
  """

  bearerToken = _messages.StringField(1)
  clientCertificate = _messages.StringField(2)
  clientKey = _messages.StringField(3)
  clusterCaCertificate = _messages.StringField(4)
  password = _messages.StringField(5)
  user = _messages.StringField(6)


class NodeConfig(_messages.Message):
  """A NodeConfig object.

  Fields:
    machineType: The name of a Google Compute Engine machine type (e.g.
      n1-standard-1).  If unspecified, the default machine type is
      n1-standard-1.
    serviceAccounts: The optional list of ServiceAccounts, each with their
      specified scopes, to be made available on all of the node VMs. In
      addition to the service accounts and scopes specified, the "default"
      account will always be created with the following scopes to ensure the
      correct functioning of the cluster:   -
      https://www.googleapis.com/auth/compute, -
      https://www.googleapis.com/auth/devstorage.read_only
    sourceImage: The fully-specified name of a Google Compute Engine image.
      For example: https://www.googleapis.com/compute/v1/projects/debian-
      cloud/global/images/backports-debian-7-wheezy-vYYYYMMDD (where YYYMMDD
      is the version date).  If specifying an image, you are responsible for
      ensuring its compatibility with the Debian 7 backports image. We
      recommend leaving this field blank to accept the default backports-
      debian-7-wheezy value.
  """

  machineType = _messages.StringField(1)
  serviceAccounts = _messages.MessageField('ServiceAccount', 2, repeated=True)
  sourceImage = _messages.StringField(3)


class Operation(_messages.Message):
  """Defines the operation resource. All fields are output only.

  Enums:
    OperationTypeValueValuesEnum: The operation type.
    StatusValueValuesEnum: The current status of the operation.

  Fields:
    errorMessage: If an error has occurred, a textual description of the
      error.
    name: The server-assigned ID for the operation.
    operationType: The operation type.
    selfLink: Server-defined URL for the resource.
    status: The current status of the operation.
    target: [Optional] The URL of the cluster resource that this operation is
      associated with.
    targetLink: Server-defined URL for the target of the operation.
    zone: The name of the Google Compute Engine zone in which the operation is
      taking place.
  """

  class OperationTypeValueValuesEnum(_messages.Enum):
    """The operation type.

    Values:
      createCluster: <no description>
      deleteCluster: <no description>
    """
    createCluster = 0
    deleteCluster = 1

  class StatusValueValuesEnum(_messages.Enum):
    """The current status of the operation.

    Values:
      done: <no description>
      pending: <no description>
      running: <no description>
    """
    done = 0
    pending = 1
    running = 2

  errorMessage = _messages.StringField(1)
  name = _messages.StringField(2)
  operationType = _messages.EnumField('OperationTypeValueValuesEnum', 3)
  selfLink = _messages.StringField(4)
  status = _messages.EnumField('StatusValueValuesEnum', 5)
  target = _messages.StringField(6)
  targetLink = _messages.StringField(7)
  zone = _messages.StringField(8)


class ServiceAccount(_messages.Message):
  """A Compute Engine service account.

  Fields:
    email: Email address of the service account.
    scopes: The list of scopes to be made available for this service account.
  """

  email = _messages.StringField(1)
  scopes = _messages.StringField(2, repeated=True)


class StandardQueryParameters(_messages.Message):
  """Query parameters accepted by all methods.

  Enums:
    AltValueValuesEnum: Data format for the response.

  Fields:
    alt: Data format for the response.
    fields: Selector specifying which fields to include in a partial response.
    key: API key. Your API key identifies your project and provides you with
      API access, quota, and reports. Required unless you provide an OAuth 2.0
      token.
    oauth_token: OAuth 2.0 token for the current user.
    prettyPrint: Returns response with indentations and line breaks.
    quotaUser: Available to use for quota purposes for server-side
      applications. Can be any arbitrary string assigned to a user, but should
      not exceed 40 characters. Overrides userIp if both are provided.
    trace: A tracing token of the form "token:<tokenid>" or "email:<ldap>" to
      include in api requests.
    userIp: IP address of the site where the request originates. Use this if
      you want to enforce per-user limits.
  """

  class AltValueValuesEnum(_messages.Enum):
    """Data format for the response.

    Values:
      json: Responses with Content-Type of application/json
    """
    json = 0

  alt = _messages.EnumField('AltValueValuesEnum', 1, default=u'json')
  fields = _messages.StringField(2)
  key = _messages.StringField(3)
  oauth_token = _messages.StringField(4)
  prettyPrint = _messages.BooleanField(5, default=True)
  quotaUser = _messages.StringField(6)
  trace = _messages.StringField(7)
  userIp = _messages.StringField(8)


