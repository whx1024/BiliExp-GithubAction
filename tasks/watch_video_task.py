from BiliClient import asyncbili
import logging

import asyncio
import random
import time
import math


class WatchVideoTask:

    def __init__(self, biliapi, enable, room_id, run_time):
        self.biliapi = biliapi
        self.enable = enable
        self.room_id = room_id
        self.run_time = run_time * 60 * 60
        self.start_time = time.time()
        self.need_vlist = {}

    async def get_need_vlist(self, Room_Id):
        if Room_Id not in self.need_vlist:
            logging.info(f"获取 up 主{Room_Id}的视频列表")
            need_vlist = []
            data = await self.biliapi.spaceArcSearch(Room_Id)
            pages = int(math.ceil(data["data"]["page"]["count"] / 100))
            for i in range(pages):
                data = await self.biliapi.spaceArcSearch(Room_Id, i + 1)
                need_vlist.extend(data["data"]["list"]["vlist"])
            self.need_vlist[Room_Id] = need_vlist

    async def work(self):
        if not self.enable:
            return

        logging.info("检查观看视频任务")

        # 必须有房间号才能运行
        if not self.room_id:
            logging.warning("观看视频模块up主号未配置,已停止...")
        else:
            await self.watch()

    async def watch(self):
        sleep_time = random.randint(0, 15)
        logging.info(f'睡眠{sleep_time}秒，与其他任务错时启动')
        await asyncio.sleep(sleep_time)
        var = 0
        while True:
            var += 1
            if isinstance(self.room_id, list):
                Room_Id = random.choice(self.room_id)
            elif isinstance(self.room_id, str):
                Room_Id = random.choice(self.room_id.split(","))
            else:
                Room_Id = self.room_id
            logging.info("本次观看视频为第 %s 次，选择UP %s" % (var, Room_Id))
            await self.get_need_vlist(Room_Id)
            video = random.choice(self.need_vlist[Room_Id])

            logging.info("本次观看选择视频为标题  %s，BV： %s" % (video["title"], video["bvid"]))

            # 获取视频分P
            video_data = await self.biliapi.getVideoPages(video['bvid'])

            for p in range(len(video_data["data"])):
                logging.info("正在观看 %s 第 %d p，共 %d p" % (video["bvid"], p + 1, len(video_data["data"])))
                video_cid = video_data["data"][p]["cid"]
                video_duration = video_data["data"][p]["duration"]

                start_ts = time.time()
                for i in range(video_duration // 15 + 1):
                    if time.time() - self.start_time > self.run_time:
                        logging.info('达到最大运行时长，退出运行')
                        return
                    await self.biliapi.watchVideoHeartBeat(video['aid'], video_cid, video['bvid'], video['mid'], i * 15,
                                                           start_ts = start_ts)
                    if i < video_duration // 15:
                        await asyncio.sleep(15)
                    elif video_duration > i * 15:
                        await asyncio.sleep(video_duration - i * 15)
                        await self.biliapi.watchVideoHeartBeat(video['aid'], video_cid, video['bvid'], video['mid'], video_duration,
                                                               start_ts = start_ts)


async def watch_video_task(biliapi: asyncbili, task_config: dict) -> None:
    worker = WatchVideoTask(biliapi, **task_config)
    await worker.work()