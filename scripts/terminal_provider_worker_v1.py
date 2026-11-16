"""One fixed-origin HTTP request. Credential arrives on a private stdin pipe only."""
import http.client
import json
from pathlib import Path
import ssl
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from scoped_credentials import sanitize, sanitized_error


def serve(value):
    key=value['credential']
    connection=http.client.HTTPSConnection('api.openai.com',timeout=value['timeout'],context=ssl.create_default_context())
    try:
        connection.request('POST','/v1/responses',json.dumps(value['request'],ensure_ascii=False).encode('utf-8'),
                           {'Content-Type':'application/json','Authorization':'Bearer '+key,'X-Client-Request-Id':value['request_id']})
        response=connection.getresponse(); raw=response.read(1048577)
        if len(raw)>1048576: raise ValueError('RESPONSE_LIMIT')
        body=json.loads(raw)
        allowed=['id','model','status','service_tier','usage','output','error','incomplete_details']
        return sanitize({'http_status':response.status,'provider_request_id':response.getheader('x-request-id'),
                         'response':{k:body[k] for k in allowed if k in body}},(key,))
    except Exception as exc:
        return {'error':sanitized_error(exc)}
    finally: connection.close()


if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(2097153)
        if len(raw)>2097152: raise ValueError('INPUT_LIMIT')
        result=serve(json.loads(raw))
    except Exception as exc: result={'error':sanitized_error(exc)}
    print(json.dumps(result,ensure_ascii=False))
