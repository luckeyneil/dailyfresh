from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FastDFSStorage(Storage):
    """
    自定义文件存储系统：
    1.需要重写2个方法，_open(), _save()
        1.1 因为下载通过nginx，不走django，所以_open()方法可直接pass
        1.2 重写_save()方法
            1.2.1 创建客户端对象client
            1.2.2 获取要上传文件的内容content
            1.2.3 通过client上传文件内容content
            1.2.4 判断是否上传成功
                1.2.4.1 若成功，返回保存的文件路径
                1.2.4.2 若失败，抛出异常‘上传失败’

    2.重写exists方法，来判断Django中是否存在文件，因为确实不存在，所以直接返回False
    3.重写url()方法，方便在Html中调用时直接使用，将nginx的域名拼接起来，返回完整地址
    """

    def __init__(self, client_conf=None, server_ip=None):
        """
        两个参数，即settings中的两个配置
        CLIENT_CONF, fdfs客户端配置文件路径，
        SERVER_IP, nginx服务器ip，
        """
        if client_conf is None:
            client_conf = settings.CLIENT_CONF
        self.client_conf = client_conf

        if server_ip is None:
            server_ip = settings.SERVER_IP
        self.server_ip = server_ip

    def _open(self, *args, **kwargs):
        """
        读取文件时调用，因为不用django读取，所以直接pass
        :param args:
        :param kwargs:
        :return:
        """
        pass

    def _save(self, file_name, content_obj):
        """
        上传文件时调用，
        :param file_name: 上传的文件名
        :param content_obj: 上传的文件对象
        :return: 返回上传后文件路径或抛出异常
        """
        # 1.2 重写_save()方法
        #     1.2.1 创建客户端对象client
        client = Fdfs_client(self.client_conf)

        #     1.2.2 获取要上传文件的内容content
        content = content_obj.read()

        #     1.2.3 通过client上传文件内容content
        try:
            ret = client.upload_by_buffer(content)
        except Exception as e:
            print(e)
            raise e

        # 1.2.4 判断是否上传成功

        # ret = {
        # 	'Group name':'group1',
        # 	'Status':'Upload successed.',
        # 	'Remote file_id':'group1/M00/00/00/wKjzh0_xaR63RExnAAAaDqbNk5E1398.py',
        # 	'Uploaded size':'6.0KB',
        # 	'Local file name':'test',
        # 	 'Storage IP':'192.168.243.133'
        # }

        if ret.get('Status') == 'Upload successed.':
            #         1.2.4.1 若成功，返回保存的文件路径
            return ret.get('Remote file_id')
        # 1.2.4.2 若失败，抛出异常‘上传失败’
        else:
            raise Exception('上传文件失败')

    def exists(self, name):
        """
        判断文件是否存在的，因为并不存在django中，所以直接返回False
        :param name:
        :return:
        """
        return False

    def url(self, name):
        """
        便在Html中调用时直接使用，将nginx的域名拼接起来，返回完整地址
        :param name:
        :return:
        """
        return self.server_ip + name
