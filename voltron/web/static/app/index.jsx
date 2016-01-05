var $ = require('jquery');
window.jQuery = $;
window.$ = $;

require('font-awesome-webpack');
require('bootstrap-webpack');
require('bootstrap');

require('../css/pygments/solarized_dark.css');

var React = require('react');
var ReactDOM = require('react-dom');
var ReactBootstrap = require('react-bootstrap');
var LinkedStateMixin = require('react-addons-linked-state-mixin');

var yaml = require('js-yaml');

var Navbar = ReactBootstrap.Navbar;
var Nav = ReactBootstrap.Nav;
var NavDropdown = ReactBootstrap.NavDropdown;
var NavItem = ReactBootstrap.NavItem;
var MenuItem = ReactBootstrap.MenuItem;
var Grid = ReactBootstrap.Grid;
var Row = ReactBootstrap.Row;
var Col = ReactBootstrap.Col;
var Table = ReactBootstrap.Table;
var Panel = ReactBootstrap.Panel;
var Modal = ReactBootstrap.Modal;
var Button = ReactBootstrap.Button;
var Input = ReactBootstrap.Input;
var ButtonInput = ReactBootstrap.ButtonInput;
var ButtonToolbar = ReactBootstrap.ButtonToolbar;
var Alert = ReactBootstrap.Alert;


var SettingsView = React.createClass({
    getInitialState: function() {
        return {disabled: true, style: "error", config: "", dirty: false, alert: 'Loading...', alertStyle: 'info'};
    },

    componentDidMount: function() {
        this.loadConfig();
    },

    loadConfig: function() {
        $.ajax({
            type: "GET",
            url: "/ui/config",
            success: function(data) {
                this.updateConfig(JSON.stringify(data, null, 4))
                this.setState({dirty: false, alert: "Loaded config", alertStyle: "success"})
            }.bind(this),
            error: function(errMsg) {
                console.log(errMsg);
                this.setState({alert: "Error loading config", alertStyle: "danger"})
            }.bind(this)
        });
    },

    handleChange: function(event) {
        this.updateConfig(event.target.value)
        this.setState({dirty: true})
    },

    updateConfig: function(data) {
        try {
            config = JSON.parse(data);
            this.setState({config: config, configStr: data, disabled: false, style: "success"});
        } catch (e) {
            console.log(e)
            this.setState({configStr: data, disabled: true, style: "danger"});
        }
    },

    save: function() {
        $.ajax({
            type: "POST",
            url: "/ui/config",
            dataType : 'json',
            contentType: 'application/json',
            data : JSON.stringify(this.state.config),
            success: function(data) {
                this.updateConfig(JSON.stringify(data, null, 4))
                this.setState({dirty: false, alert: "Saved config", alertStyle: "success"})
            }.bind(this),
            error: function(errMsg) {
                console.log(errMsg);
                this.loadConfig();
                this.setState({dirty: false, alert: "Error saving config", alertStyle: "error"})
            }.bind(this)
        });
    },

    cancel: function() {
        this.loadConfig()
    },

    render: function() {
        return (
            <Grid style={{marginTop: "60px"}}>
                <Row>
                    <Col xs={12}>
                        <h2>Settings</h2>
                        <form>
                            <Input type="textarea" bsStyle={this.state.style} label="Config" ref="config" rows={24}
                                value={this.state.configStr} onChange={this.handleChange} />
                            <Alert bsStyle={this.state.alertStyle}>{this.state.alert}</Alert>
                            <ButtonToolbar>
                                <Button bsStyle="primary" disabled={this.state.disabled} onClick={this.save}>Save</Button>
                                <Button disabled={!this.state.dirty} onClick={this.cancel}>Cancel</Button>
                            </ButtonToolbar>
                        </form>
                    </Col>
                </Row>
            </Grid>
        );
    }
});


var APIView = React.createClass({
    mixins: [LinkedStateMixin],

    getInitialState: function() {
        return {selectedRequest: "version", request: JSON.stringify({request: "version"}, null, 4), response: "",
                config: "", alert: "Ready to send request",
                alertStyle: 'info', plugins:{}};
    },

    componentDidMount: function() {
        $.ajax({
            type: "GET",
            url: "/api/plugins",
            success: function(data) {
                this.setState({plugins: data.data.plugins.api})
            }.bind(this)
        });
    },

    send: function() {
        this.setState({alert: "Sending request...", alertStyle: "info"})
        $.ajax({
            type: "POST",
            url: "/api/request",
            dataType : 'json',
            contentType: 'application/json',
            data : this.state.request,
            success: function(data) {
                this.setState({response: JSON.stringify(data, null, 4),
                               alert: "Sent request and received response",
                               alertStyle: "success"})
            }.bind(this),
            error: function(errMsg) {
                console.log(errMsg);
                this.setState({response: "", alert: "Error sending request", alertStyle: "danger"})
            }.bind(this)
        });
    },

    selectRequest: function(event) {
        this.setState({selectedRequest: event.target.value,
                       request: JSON.stringify({request: event.target.value}, null, 4)})
    },

    changeField: function(field, event) {
        var request = JSON.parse(this.state.request);
        if (!request.data) {
            request.data = {};
        }
        request.data[field] = JSON.parse(event.target.value);
        this.setState({request: JSON.stringify(request, null, 4)});
    },

    render: function() {
        var requests = Object.keys(this.state.plugins).map(function(key, i) {
            return (<option value={key} key={key}>{key}</option>)
        });

        var fields = [];
        if (this.state.selectedRequest in this.state.plugins) {
            fields = Object.keys(this.state.plugins[this.state.selectedRequest].request).map(function(field, i) {
                return (
                    <Row key={field}>
                        <Col xs={6}>
                            <Input type="text" label={field} placeholder=""onChange={this.changeField.bind(this, field)}/>
                        </Col>
                    </Row>
                )
            }.bind(this));
        }

        return (
            <Grid style={{marginTop: "60px"}}>
                <Row><Col xs={12}><h2>API</h2></Col></Row>
                <Row>
                    <Col xs={2}>
                        <Input type="select" label="Request" placeholder="select" onChange={this.selectRequest}>
                            {requests}
                        </Input>
                    </Col>
                </Row>
                {fields}
                <Row>
                    <Col xs={6}>
                        <Input rows={24} valueLink={this.linkState('request')} type="textarea" label="Request"/>
                    </Col>
                    <Col xs={6}><Input rows={24} value={this.state.response} type="textarea" label="Response"/></Col>
                </Row>
                <Row>
                    <Col xs={12}>
                        <Alert bsStyle={this.state.alertStyle}>{this.state.alert}</Alert>
                        <ButtonToolbar>
                            <Button bsStyle="primary" onClick={this.send}>Send</Button>
                        </ButtonToolbar>
                    </Col>
                </Row>
            </Grid>
        );
    }
});


var ViewsView = React.createClass({
    mixins: [LinkedStateMixin],

    getInitialState: function() {
        return {plugins:[]};
    },

    componentDidMount: function() {
        $.ajax({
            type: "GET",
            url: "/api/plugins",
            success: function(data) {
                this.setState({plugins: data.data.plugins.web})
            }.bind(this)
        });
    },

    render: function() {
        var views = this.state.plugins.map(function(key, i) {
            return (
                <Row key={key}>
                     <Col xs={12}>
                        <a href={'/view/'+key+'/index.html'}>{key}</a>
                    </Col>
                </Row>
            )
        });

        return (
            <Grid style={{marginTop: "60px"}}>
                <Row><Col xs={12}><h2>Views</h2></Col></Row>
                <Row><Col xs={12}><b>The following view plugins are installed:</b></Col></Row>
                {views}
            </Grid>
        );
    }
});


var MainNav = React.createClass({
    selectView: function(view) {
        this.props.selectView(view)
    },
    render: function() {
        return (
            <Navbar inverse fixedTop>
                <Navbar.Header>
                    <Navbar.Brand>voltron</Navbar.Brand>
                </Navbar.Header>
                <Nav>
                    <NavItem eventKey={1} onSelect={this.selectView.bind(this, APIView)} href="#">API</NavItem>
                    <NavItem eventKey={2} onSelect={this.selectView.bind(this, ViewsView)} href="#">Plugins</NavItem>
                </Nav>
                <Nav pullRight>
                    <NavItem eventKey={3} onSelect={this.selectView.bind(this, SettingsView)} href="#">Settings</NavItem>
                </Nav>
            </Navbar>
        );
    }
});




var MainView = React.createClass({
    getInitialState: function() {
        return {view: (<div/>)};
    },
    selectView: function(view) {
        this.setState({view: React.createFactory(view)()});
    },
    render: function() {
        return (
            <div>
                <MainNav logout={this.logout} username={this.state.username} selectView={this.selectView}/>
                {this.state.view}
            </div>
        );
    }
});


ReactDOM.render(
    <MainView/>,
    document.getElementById('main')
);
