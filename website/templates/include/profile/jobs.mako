<script id="profileJobs" type="text/html">

    <div data-bind="if: mode() === 'edit'">

        <form role="form" data-bind="submit: submit">

            <div data-bind="sortable: {
                    data: contents,
                    options: {
                        handle: '.sort-handle',
                        containment: '#containDrag'
                    }
                }">

                <div>

                    <div class="well well-sm sort-handle">
                        <span>Position {{ $index() + 1 }}</span>
                        <span data-bind="visible: $parent.hasMultiple()">
                            [ drag to reorder ]
                        </span>
                        <a
                                class="text-danger pull-right"
                                data-bind="click: $parent.removeContent,
                                           visible: $parent.canRemove"
                            >Remove</a>
                    </div>

                    <div class="form-group">
                        <label>Institution / Employer</label>
                        <input class="form-control" data-bind="value: institution" />
                    </div>

                    <div class="form-group">
                        <label>Department</label>
                        <input class="form-control" data-bind="value: department" />
                    </div>

                    <div class="form-group">
                        <label>Job Title</label>
                        <input class="form-control" data-bind="value: title" />
                    </div>

                    <div class="form-group">
                        <label>Start Date</label>
                        <div class="row">
                            <div class ="col-md-3">
                                <select class="form-control" data-bind="options: startMonths,
                                         optionsCaption: 'Month',
                                         value: startMonth">
                                </select>
                            </div>
                            <div class="col-md-4">
                                <input class="form-control" placeholder="Year" data-bind="value: startYear" />
                            </div>
                        </div>
                    </div>
                    <p data-bind="validationMessage: start, style:{color: 'red'}" ></p>


                    <div class="form-group" data-bind="ifnot: ongoing">
                        <label>End Date</label>
                            <div class="row">
                                <div class ="col-md-3">
                                    <select class="form-control" data-bind="options: endMonths,
                                         optionsCaption: 'Month',
                                         value: endMonth">
                                    </select>
                                </div>
                                <div class="col-md-4">
                                    <input class="form-control" placeholder="Year" data-bind="value: endYear" />
                                </div>
                            </div>
                    </div>


                    <div class="form-group">
                        <label>Ongoing</label>
                        <input type="checkbox" data-bind="checked: ongoing, click: clearEnd"/>
                    </div>

                    <!--knockout validation messages-->
                        <p data-bind="validationMessage: end, style:{color: 'red'}"></p>
                    <!--->

                    <hr data-bind="visible: $index() != ($parent.contents().length - 1)" />

                </div>

            </div>

            <div>
                <a class="btn btn-default" data-bind="click: addContent">
                    Add another
                </a>
            </div>

            <div class="padded">

                <button
                        type="submit"
                        class="btn btn-default"
                        data-bind="visible: viewable, click: cancel"
                    >Cancel</button>

                <button
                        type="submit"
                        class="btn btn-primary"
                        data-bind="enable: enableSubmit"
                    >Submit</button>

            </div>

            <!-- Flashed Messages -->
            <div class="help-block">
                <p data-bind="html: message, attr.class: messageClass"></p>
            </div>

        </form>

    </div>

    <div data-bind="if: mode() === 'view'">

        <div data-bind="ifnot: contents().length">
            <div class="well well-sm">Not provided</div>
        </div>

        <div data-bind="if: contents().length">

            <table class="table">

                <thead>
                    <tr>
                        <th>Institution</th>
                        <th>Department</th>
                        <th>Title</th>
                        <th>Start&nbsp;Date</th>
                        <th>End&nbsp;Date</th>
                    </tr>
                </thead>

                <tbody data-bind="foreach: contents">

                    <tr>

                        <td>{{ institution }}</td>
                        <td>{{ department }}</td>
                        <td>{{ title }}</td>
                        <td>{{ startMonth }} {{ startYear }}</td>
                        <td>{{ endView }}</td>

                    </tr>

                </tbody>

            </table>

        </div>

        <div data-bind="if: editable">
            <a class="btn btn-default" data-bind="click: edit">Edit</a>
        </div>

    </div>

</script>
