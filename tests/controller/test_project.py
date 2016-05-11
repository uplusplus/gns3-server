#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import pytest
import aiohttp
from unittest.mock import MagicMock
from tests.utils import AsyncioMagicMock
from unittest.mock import patch
from uuid import uuid4

from gns3server.controller.project import Project
from gns3server.config import Config


def test_affect_uuid():
    p = Project()
    assert len(p.id) == 36

    p = Project(project_id='00010203-0405-0607-0809-0a0b0c0d0e0f')
    assert p.id == '00010203-0405-0607-0809-0a0b0c0d0e0f'


def test_json(tmpdir):
    p = Project()
    assert p.__json__() == {"name": p.name, "project_id": p.id, "temporary": False, "path": p.path}


def test_path(tmpdir):

    directory = Config.instance().get_section_config("Server").get("project_directory")

    with patch("gns3server.compute.project.Project._get_default_project_directory", return_value=directory):
        p = Project(project_id=str(uuid4()))
        assert p.path == os.path.join(directory, p.id)
        assert os.path.exists(os.path.join(directory, p.id))


def test_init_path(tmpdir):

    p = Project(path=str(tmpdir), project_id=str(uuid4()))
    assert p.path == str(tmpdir)


def test_changing_path_with_quote_not_allowed(tmpdir):
    with pytest.raises(aiohttp.web.HTTPForbidden):
        p = Project(project_id=str(uuid4()))
        p.path = str(tmpdir / "project\"53")


def test_captures_directory(tmpdir):
    p = Project(path=str(tmpdir))
    assert p.captures_directory == str(tmpdir / "project-files" / "captures")
    assert os.path.exists(p.captures_directory)


def test_addCompute(async_run):
    compute = MagicMock()
    project = Project()
    async_run(project.addCompute(compute))
    assert compute in project._computes


def test_addVM(async_run):
    compute = MagicMock()
    project = Project()

    response = MagicMock()
    response.json = {"console": 2048}
    compute.post = AsyncioMagicMock(return_value=response)

    vm = async_run(project.addVM(compute, None, name="test", vm_type="vpcs", properties={"startup_config": "test.cfg"}))

    compute.post.assert_any_call('/projects/{}/vpcs/vms'.format(project.id),
                                 data={'vm_id': vm.id,
                                       'console_type': 'telnet',
                                       'startup_config': 'test.cfg',
                                       'name': 'test'})
    assert compute in project._project_created_on_compute


def test_getVM(async_run):
    compute = MagicMock()
    project = Project()

    response = MagicMock()
    response.json = {"console": 2048}
    compute.post = AsyncioMagicMock(return_value=response)

    vm = async_run(project.addVM(compute, None, name="test", vm_type="vpcs", properties={"startup_config": "test.cfg"}))
    assert project.getVM(vm.id) == vm

    with pytest.raises(aiohttp.web_exceptions.HTTPNotFound):
        project.getVM("test")


def test_addLink(async_run):
    compute = MagicMock()
    project = Project()

    response = MagicMock()
    response.json = {"console": 2048}
    compute.post = AsyncioMagicMock(return_value=response)

    vm1 = async_run(project.addVM(compute, None, name="test1", vm_type="vpcs", properties={"startup_config": "test.cfg"}))
    vm2 = async_run(project.addVM(compute, None, name="test2", vm_type="vpcs", properties={"startup_config": "test.cfg"}))
    link = async_run(project.addLink())
    async_run(link.addVM(vm1, 3, 1))
    async_run(link.addVM(vm2, 4, 2))
    assert len(link._vms) == 2


def test_getLink(async_run):
    compute = MagicMock()
    project = Project()

    response = MagicMock()
    response.json = {"console": 2048}
    compute.post = AsyncioMagicMock(return_value=response)

    link = async_run(project.addLink())
    assert project.getLink(link.id) == link

    with pytest.raises(aiohttp.web_exceptions.HTTPNotFound):
        project.getLink("test")


def test_emit(async_run):
    project = Project()
    with project.queue() as queue:
        assert len(project._listeners) == 1
        async_run(queue.get(0.1))  #  ping
        project.emit('test', {})
        notif = async_run(queue.get(5))
        assert notif == ('test', {}, {})

    assert len(project._listeners) == 0
