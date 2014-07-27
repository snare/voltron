angular.module('VoltronApp.services', []).
factory('voltronAPIservice', function($http)
{
    var voltronAPI = {};

    function createRequest(requestType, data) {
        return {type: "request", request: requestType, data: data}
    }

    voltronAPI.request = function(request) {
        return $http({
            method: 'POST',
            url: '/api/request',
            data: request
        });
    }

    voltronAPI.disassemble = function(address, count) {
        return $http({
            method: 'POST',
            url: '../api/request',
            data: createRequest('disassemble', {address: address, count: count})
        });
    }

    voltronAPI.executeCommand = function(command) {
        return voltronAPI.request(createRequest('execute_command', {command: command}))
    }

    voltronAPI.listTargets = function() {
        return voltronAPI.request(createRequest('list_targets', {}))
    }

    voltronAPI.readMemory = function(address, length) {
        return voltronAPI.request(createRequest('read_memory', {address: address, length: length}))
    }

    voltronAPI.readRegisters = function() {
        return voltronAPI.request(createRequest('read_registers', {}))
    }

    voltronAPI.readStack = function(length) {
        return voltronAPI.request(createRequest('read_stack', {length: length}))
    }

    voltronAPI.state = function() {
        return voltronAPI.request(createRequest('state', {}))
    }

    voltronAPI.version = function() {
        return voltronAPI.request(createRequest('version', {}))
    }

    voltronAPI.wait = function(timeout) {
        // return voltronAPI.request(createRequest('wait', {timeout: timeout}))
        return $http({
            method: 'GET',
            url: '/api/wait?timeout='+timeout
        });
    }

    return voltronAPI;
});
