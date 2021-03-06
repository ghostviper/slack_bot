# coding=utf-8

# 百度地图
import re
from datetime import datetime

import requests


REGEX = re.compile(ur'从(\w+)[\u53bb|\u5230](\w+)', re.UNICODE)
HTML_REGEX = re.compile(r'(<.*?>)')
SUGGESTION_API = 'http://api.map.baidu.com/place/v2/suggestion'
DIRECTION_API = 'http://api.map.baidu.com/direction/v1'

DIRECTION = 0
NODIRECTION = 1
NOSCHEME = 2


def place_suggestion(ak, pos):
    res = requests.get(SUGGESTION_API, params={
        'query': pos, 'region': 131, 'ak': ak, 'output': 'json'})
    return [r['name'] for r in res.json()['result']]


def place_direction(ak, origin, destination, mode='transit', tactics=11,
                    region='北京', origin_region='北京',
                    destination_region='北京'):
    params = {
        'origin': origin, 'destination': destination, 'ak': ak,
        'output': 'json', 'mode': mode, 'tactics': tactics
    }
    if mode != 'transit':
        params.update({
            'origin_region': origin_region,
            'destination_region': destination_region
        })
    else:
        params.update({'region': region})
    res = requests.get(DIRECTION_API, params=params).json()
    result = res.get('result', [])

    # type=1起终点模糊
    if res['type'] == 1:
        if not result:
            return (NOSCHEME, place_suggestion(ak, origin),
                    place_suggestion(ak, destination))
        if mode != 'transit':
            _origin = result['origin']['content']
            _dest = result['destination']['content']
        else:
            _origin = result.get('origin', [])
            _dest = result.get('destination', [])
        o = ['{0}: {1}'.format(r['name'].encode('utf-8'),
                               r['address'].encode('utf-8')) \
             for r in _origin]
        d = ['{0}: {1}'.format(r['name'].encode('utf-8'),
                               r['address'].encode('utf-8')) \
             for r in _dest]
        return (NODIRECTION, o, d)
    # 起终点明确
    if mode == 'driving':
        # 驾车
        taxi = result['taxi']
        for d in taxi['detail']:
            if u'白天' in d['desc']:
                daytime = d
            else:
                night = d
        is_daytime = 5 < datetime.now().hour < 23
        price = daytime['total_price'] if is_daytime else night['total_price']
        remark = taxi['remark']
        taxi_text = u'{0} 预计打车费用 {1}元'.format(remark, price)
        steps = result['routes'][0]['steps']
        steps = [re.sub(HTML_REGEX, '', s['instructions']) for s in steps]
        return (DIRECTION, '\n'.join(steps), taxi_text)
    elif mode == 'walking':
        steps = result['routes'][0]['steps']
        steps = [re.sub(HTML_REGEX, '', s['instructions']) for s in steps]
        return (DIRECTION, '\n'.join(steps), '')
    else:
        schemes = result['routes']
        steps = []
        for index, scheme in enumerate(schemes, 1):
            scheme = scheme['scheme'][0]
            step = '*方案{0} [距离: {1}公里, 花费: {2}元, 耗时: {3}分钟]:\n'.format(
                index, scheme['distance'] / 1000,
                scheme['price'] / 100,
                scheme['duration'] / 60)
            step += '\n'.join([
                re.sub(HTML_REGEX, '',
                       s[0]['stepInstruction'].encode('utf-8'))
                for s in scheme['steps']
            ])
            step += '\n' + '-' * 40
            steps.append(step)
        return (DIRECTION, steps, '')


def test(data, bot):
    message = data['message']
    if not isinstance(message, unicode):
        message = message.decode('utf-8')
    return REGEX.search(message)


def handle(data, bot, kv, app):
    if app is None:
        ak = '18691b8e4206238f331ad2e1ca88357e'
    else:
        ak = app.config.get('BAIDU_AK')
    message = data['message']
    if not isinstance(message, unicode):
        message = message.decode('utf-8')
    origin, dest = REGEX.search(message).groups()

    tmpl = '最优路线: {0} {1}'
    if any([text in message for text in [u'开车', u'驾车']]):
        mode = 'driving'
        tmpl = '最优路线: {0} \n[{1}]'
    elif u'步行' in message:
        mode = 'walking'
    else:
        # 公交
        mode = 'transit'

    result = place_direction(ak, origin, dest, mode)
    if result[0] == NOSCHEME:
        text = '\n'.join(['输入的太模糊了, 你要找得起点可以选择:',
                          '|'.join(result[1]),
                          '终点可以选择:',
                          '|'.join(result[2])])
    elif result[0] == NODIRECTION:
        reg = ''
        if result[1]:
            reg += '起点'
        if result[2]:
            reg += '终点'
        msg = ['输入的{}太模糊了: 以下是参考:'.format(reg)] + \
            result[1] + result[2]

        text = '\n'.join(msg)
    else:
        if isinstance(result[1], list):
            _result = '\n'.join(result[1])
        else:
            _result = result[1].encode('utf-8')
        text = tmpl.format(_result, result[2].encode('utf-8'))
    return text


if __name__ == '__main__':
    print handle({'message': '我想从兆维工业园到北京南站'}, None, None, None)
#    print handle({'message': '我想从人大到北京南站'}, None, None, None)
#    print handle({'message': '我想从人大到豆瓣'}, None, None, None)
#    print handle({'message': '我想从兆维工业园到北京南站 步行'}, None, None, None)
#    print handle({'message': '我想从兆维工业园到北京南站 开车'}, None, None, None)
#    print handle({'message': '从酒仙桥去798'}, None, None, None)
